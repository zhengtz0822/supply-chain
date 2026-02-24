# 依赖安装命令:
# pip install pandas openpyxl xlrd agentscope
import logging
import os
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pandas as pd
# AgentScope 导入
import agentscope
from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from langchain_core.messages import HumanMessage
# LangChain 导入 (仅用于 call_llm_for_address_refinement)
from langchain_openai import ChatOpenAI

# 配置导入
from app.core.config import get_settings
from app.schemas.address import (
    AddressColumnInfo,
    AddressRefinementData,
    AddressMatchSource,
    AddressMatchResult,
    AddressMatchCandidate,
    AddressMatchTaskConfig,
    AddressDetailData,
)
from app.tools.tool_registry import create_fresh_toolkit

# mcp工具导入
# from app.tools.tool_registry import get_toolkit

# 配置日志
logger = logging.getLogger(__name__)




class AddressService:
    """
    地址解析服务
    从CSV/Excel文件中识别和提取地址列数据
    """

    # 中文地址关键词
    ADDRESS_KEYWORDS = [
        '省', '市', '区', '县', '镇', '乡', '村',
        '街道', '路', '巷', '号', '弄', '栋',
        '大道', '小区', '大厦', '花园', '城', '庄',
        '苑', '楼', '广场', '中心', '公寓', '广场'
    ]

    # 排除的列名（不区分大小写）
    EXCLUDED_COLUMN_NAMES = [
        'id', '编号', '序号', 'no', 'number', 'code',
        '编码', 'code', '电话', '手机', 'phone', 'mobile',
        'tel', '邮箱', 'email', 'mail', '姓名', 'name',
        '时间', 'time', '日期', 'date', '备注', 'remark'
    ]

    @staticmethod
    def read_file(file_path: str) -> Optional[pd.DataFrame]:
        """
        根据文件扩展名读取文件
        支持 .csv 和 .xlsx/.xls 文件
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        try:
            if suffix == '.csv':
                # 尝试多种编码读取CSV
                encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        return df
                    except UnicodeDecodeError:
                        continue
                raise ValueError("无法识别CSV文件编码")

            elif suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl' if suffix == '.xlsx' else 'xlrd')
                return df

            else:
                raise ValueError(f"不支持的文件类型: {suffix}")

        except Exception as e:
            raise ValueError(f"读取文件失败: {str(e)}")

    @staticmethod
    def is_address_column(
        column_name: str,
        series: pd.Series,
        sample_size: int = 10
    ) -> Tuple[bool, Optional[AddressColumnInfo]]:
        """
        判断一列是否为地址列

        Args:
            column_name: 列名
            series: 列数据
            sample_size: 采样数量

        Returns:
            (是否为地址列, 列信息)
        """
        # 检查列名是否在排除列表中
        if column_name.lower() in [name.lower() for name in AddressService.EXCLUDED_COLUMN_NAMES]:
            return False, None

        # 获取非空值进行采样
        non_null_values = series.dropna().astype(str).tolist()

        if len(non_null_values) == 0:
            return False, None

        # 采样前N行非空数据
        samples = non_null_values[:sample_size]

        valid_count = 0
        keyword_match_count = 0

        for value in samples:
            # 跳过空字符串
            if not value or value.strip() == '' or value.lower() == 'nan':
                continue

            value = value.strip()

            # 检查1: 文本长度在 5 到 100 个字符之间
            if len(value) < 5 or len(value) > 100:
                continue

            # 检查2: 不包含 @、/、\ 等邮箱或路径符号
            if '@' in value or '/' in value or '\\' in value:
                continue

            # 检查3: 不是纯数字
            if value.isdigit():
                continue

            # 检查4: 包含中文地址关键词
            has_keyword = False
            for keyword in AddressService.ADDRESS_KEYWORDS:
                if keyword in value:
                    has_keyword = True
                    break

            if has_keyword:
                valid_count += 1
                keyword_match_count += 1

        # 至少有2行包含地址关键词
        if len(samples) <= 3:
            is_address = valid_count >= 1  # 样本少时，有1个匹配就够了
        else:
            is_address = valid_count >= 2  # 样本多时，仍需2个匹配

        if is_address:
            info = AddressColumnInfo(
                column_name=column_name,
                sample_count=len(samples),
                keyword_match_count=keyword_match_count
            )
            return True, info

        return False, None

    @staticmethod
    def find_address_columns(df: pd.DataFrame) -> Tuple[List[str], List[AddressColumnInfo]]:
        """
        查找数据框中所有地址列

        Returns:
            (地址列名列表, 地址列详细信息列表)
        """
        address_columns = []
        column_details = []

        for column in df.columns:
            is_addr, info = AddressService.is_address_column(column, df[column])
            if is_addr:
                address_columns.append(column)
                column_details.append(info)

        return address_columns, column_details

    @staticmethod
    def extract_and_deduplicate_addresses(
        df: pd.DataFrame,
        address_columns: List[str]
    ) -> pd.DataFrame:
        """
        提取地址列并进行去重

        Args:
            df: 原始数据框
            address_columns: 地址列名列表

        Returns:
            去重后的地址数据框
        """
        if not address_columns:
            return pd.DataFrame()

        # 提取地址列
        address_df = df[address_columns].copy()

        # 移除全为空的行
        address_df = address_df.dropna(how='all')

        # 去重：基于所有地址列的组合进行去重
        address_df = address_df.drop_duplicates()

        return address_df

    @staticmethod
    def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
        """
        保存为CSV文件，使用UTF-8-BOM编码

        Args:
            df: 数据框
            output_path: 输出文件路径
        """
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        # 使用UTF-8-BOM编码保存（Excel能正确识别）
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

    @staticmethod
    def parse_addresses_from_files(
        batch_id: str,
        file_paths: List[str],
        output_dir: str = './outputs'
    ) -> Dict:
        """
        从多个文件中解析地址数据

        Args:
            batch_id: 批次ID
            file_paths: 文件路径列表
            output_dir: 输出目录

        Returns:
            解析结果字典
        """
        all_address_columns = set()
        all_column_details = []
        all_address_data = []

        for file_path in file_paths:
            try:
                # 读取文件
                df = AddressService.read_file(file_path)

                # 查找地址列
                address_columns, column_details = AddressService.find_address_columns(df)

                if address_columns:
                    all_address_columns.update(address_columns)
                    all_column_details.extend(column_details)

                    # 提取并去重地址数据
                    address_df = AddressService.extract_and_deduplicate_addresses(
                        df, address_columns
                    )
                    all_address_data.append(address_df)

            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {str(e)}")
                continue

        # 汇总所有地址数据
        if all_address_data:
            combined_df = pd.concat(all_address_data, ignore_index=True)
            # 再次去重
            combined_df = combined_df.drop_duplicates()
            # 将 combined_df 的地址转换为字符串数组
            combined_df['addresses'] = combined_df.apply(lambda row: row.astype(str).tolist(), axis=1)
            combined_dfArray = combined_df['addresses'].tolist()
            # 调用大模型规则化地理或者是去除非地址信息
            # 展平所有地址字符串
            flat_addresses = [addr for addrs in combined_dfArray for addr in addrs]
            logger.info(f"[{batch_id}] 开始调用 LLM 处理地址数据，共 {len(flat_addresses)} 条地址")
            refinement_result = AddressService.call_llm_for_address_refinement(flat_addresses)
            logger.info(f"[{batch_id}] LLM 处理完成，识别结果: {len(refinement_result.results)} 条")

            return {
                'success': True,
                'message': f'成功从 {len(file_paths)} 个文件中提取并处理 {len(flat_addresses)} 条地址数据',
                'refinement_result': refinement_result
            }
        else:
            return {
                'success': False,
                'message': '未找到任何地址列',
                'refinement_result': None
            }
    @staticmethod
    def call_llm_for_address_refinement(address_list: List[str]) -> AddressRefinementData:
        """
        调用LLM对地址数据进行精细化处理和标准化

        使用 response_format + json_schema 实现结构化输出

        Args:
            address_list: 地址字符串列表

        Returns:
            结构化的地址识别结果
        """
        logger.info(f"[LLM] call_llm_for_address_refinement 被调用，地址数量: {len(address_list)}")

        if not address_list:
            logger.warning("[LLM] 地址列表为空，返回空结果")
            return AddressRefinementData(results=[])

        logger.info(f"[LLM] 初始化 Qwen 客户端...")
        # 初始化LLM客户端
        settings = get_settings()
        llm = ChatOpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=settings.DASHSCOPE_API_KEY,
            model="qwen-plus",
            temperature=0.7,
        )

        # 使用 response_format 配置结构化输出
        logger.info(f"[LLM] 配置结构化输出...")
        structured_llm = llm.bind(
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "address_refinement",
                    "strict": True,
                    "schema": AddressRefinementData.model_json_schema()
                }
            }
        )

        # 构建提示词
        addresses_text = "\n".join([f'"{addr}"' for addr in address_list[:10]])  # 只打印前10条避免日志过长
        logger.info(f"[LLM] 构建提示词，地址示例:\n{addresses_text}")
        logger.info(f"[LLM] 总共需要处理 {len(address_list)} 条地址")

        full_addresses_text = "\n".join([f'"{addr}"' for addr in address_list])
        prompt = f"""你是一个地址识别助手。请分析以下字符串，判断每个是否为地理位置信息。

待识别的字符串：
{full_addresses_text}

地址信息包括：
1. 标准行政地址（国家、省、市、区县、街道）
2. 非标准地址（如"XX大楼"、"XX广场"、"XX小区"）
3. 地标性建筑
4. 含有明显地理特征的描述

识别原则：
- 宽松判断：只要可能包含位置信息就标记为true
- 对于模糊不清但可能包含位置信息的，优先判断为位置
- 非地址信息（如纯测试文本、"不知道"等）标记为false

对每个字符串，返回处理后的文本（保持原样或简单清理）和是否为位置的布尔值。"""

        try:
            # 调用LLM，获得结构化输出
            logger.info(f"[LLM] 开始调用 Qwen API...")
            response = structured_llm.invoke([HumanMessage(content=prompt)])
            logger.info(f"[LLM] API 调用成功，响应内容: {response.content[:200]}...")  # 只打印前200字符

            # 解析响应内容为 Pydantic 模型
            import json
            result = AddressRefinementData.model_validate_json(response.content)
            logger.info(f"[LLM] 解析成功，结果数量: {len(result.results)}")
            return result

        except Exception as e:
            logger.error(f"[LLM] LLM地址识别处理失败: {str(e)}", exc_info=True)
            # 直接抛出异常，让整个请求失败
            raise ValueError(f"LLM地址识别失败: {str(e)}")

    @staticmethod
    def _build_address_match_prompt(distance_threshold: float) -> str:
        """
        构建地址匹配智能体的系统提示词

        Args:
            distance_threshold: 距离阈值（米）

        Returns:
            系统提示词字符串
        """
        prompt = f"""你是一个地理信息智能分析引擎，负责判断多个候选地址是否与源地址表示同一物理位置。

## 分析原则
1. **空间一致性**：优先使用经纬度计算距离（≤{distance_threshold} 米为强一致）。
2. **语义锚定**：`firstLevelAddress` 是核心 POI 标识，比 street-level 地址更重要。
3. **模糊容忍**：源地址中的"附近""旁边"等应被合理泛化，不视为不匹配。
4. **冲突处理**：若多个候选高置信且互斥 → action设为 manual_review；若无合理匹配 → action设为 keep_original。
## 使用工具
1. **地址解析工具**：如果经纬度缺失使用maps_geo工具返回经纬度。
2. **maps_text_search**: 如果需要搜索POI信息，使用该工具进行搜索
## 输出要求
请严格按照 JSON Schema 输出结果，包含：
- 只输出 JSON，不要任何其他文字、解释、Markdown（如 ```json）。
- 确保 JSON 语法完全正确：所有字段用双引号，对象间用逗号分隔，无多余字符。
- 仔细检查 "source" 和 "recommendation" 之间是否有逗号！
- 输出必须能被 Python json.loads() 直接解析。

- **source**: 源地址回显（address_text, latitude, longitude）
- 确保 "source" 和 "recommendation" 还有 matches 名称的完整性
- **recommendation**: 全局推荐信息 
  - action: 建议(新地址、相似地址)
  - suggested_candidate_id: 建议采用的候选POI ID（如果action为相似地址）
  - suggested_address_text: 建议采用的地址文本
  - overall_confidence: 整体置信度（0-1）
  - reason: 建议原因（详细说明）
- **matches**: 每个候选的匹配详情列表
  - candidate_id: 候选ID
  - address_text: 候选地址文本
  - is_same_location: 是否同一位置（布尔值）
  - confidence_score: 置信度分数（0-1）
  - distance_meters: 距离（米，如果有经纬度）
  - reason: 匹配原因（详细说明）
"""
        return prompt

    @staticmethod
    async def match_addresses(
        source: 'AddressMatchSource',
        candidates: List['AddressMatchCandidate'],
        task_config: Optional['AddressMatchTaskConfig'] = None
    ) -> Dict:
        """
        地址匹配度分析 (使用 AgentScope ReActAgent)

        判断源地址与候选地址是否描述同一地理位置

        Args:
            source: 源地址信息
            candidates: 候选地址列表
            task_config: 任务配置

        Returns:
            包含 success, message, result 的字典
        """
        logger.info(f"[地址匹配] 源地址: {source.address_text}, 候选数量: {len(candidates)}")

        # 获取配置参数
        distance_threshold = task_config.distance_threshold_meters if task_config else 100

        # 初始化 AgentScope ReActAgent
        logger.info(f"[地址匹配] 初始化 AgentScope ReActAgent...")

        # 从 settings 获取 API Key
        settings = get_settings()
        api_key = settings.DASHSCOPE_API_KEY

        # 构建系统提示词
        sys_prompt = AddressService._build_address_match_prompt(distance_threshold)
        logger.info(f"[地址匹配] 系统提示词长度: {len(sys_prompt)} 字符")
        # 打印提示词
        logger.info(f"[地址匹配] 系统提示词: \n{sys_prompt}")
        # import agentscope
        # agentscope.init(studio_url="http://localhost:3000")

        # 初始化工具,按需初始化
        toolkit = await create_fresh_toolkit()
        # 初始化 DashScope 模型
        model = DashScopeChatModel(
            model_name="qwen-plus",
            api_key=api_key,
            # base_http_api_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            stream=False
        )

        # 创建 ReActAgent
        agent = ReActAgent(
            name="address_match_agent",
            sys_prompt=sys_prompt,
            model=model,
            formatter=DashScopeChatFormatter(),
            toolkit=toolkit,
        )

        # 构建候选地址信息文本
        candidates_text = ""
        for idx, candidate in enumerate(candidates, 1):
            candidates_text += f"""
候选 {idx}:
  - ID: {candidate.candidate_id}
  - 地址文本: {candidate.address_text}
  - 完整结构化地址: {candidate.actualAddress or '无'}
  - 一级地址(POI): {candidate.firstLevelAddress or '无'}
  - 经纬度: ({candidate.latitude}, {candidate.longitude})
"""

        # 构建用户消息
        user_prompt = f"""请分析以下地址匹配任务：

## 源地址 (source)
- 地址文本: {source.address_text}
- 经纬度: ({source.latitude}, {source.longitude})

## 候选地址 (candidates)
{candidates_text}

## 任务配置
- 距离阈值: {distance_threshold} 米

请开始分析并输出结构化结果。"""

        try:
            # 调用 ReActAgent，使用 structured_model 获取结构化输出
            logger.info(f"[地址匹配] 开始调用 ReActAgent 分析...")
            # 打印用户提示词内容
            logger.info(f"[地址匹配] 用户提示词: \n{user_prompt}")

            msg = Msg(
                "user",
                user_prompt,
                "user",
            )
            # response = await agent(
            #     Msg(
            #         "user",
            #         user_prompt,
            #         "user",
            #     ),
            #     # structured_model=AddressMatchResult,
            # )
            llmResponse =  await agent( msg, structured_model=AddressMatchResult)
            # 从响应中获取结构化结果
            # 直接打印整个respmse
            logger.info(f"[地址匹配] 解析结果: \n{llmResponse}")
            result = llmResponse.metadata  # AgentScope 将结构化输出放在 metadata 字段中

            # logger.info(f"[地址匹配] 解析成功，匹配结果: action={result.recommendation.action}, 置信度={result.recommendation.overall_confidence}")

            return {
                'success': True,
                'message': f'地址匹配分析完成，建议操作:',
                'result': result
            }
            # return {
            #     'success': True,
            #     'message': f'地址匹配分析完成，建议操作:',
            #     'result': llmResponse
            # }

        except Exception as e:
            logger.error(f"[地址匹配] Agent分析失败: {str(e)}", exc_info=True)
            raise ValueError(f"地址匹配分析失败: {str(e)}")

    @staticmethod
    def _build_address_parse_prompt() -> str:
        """
        构建地址解析智能体的系统提示词

        Returns:
            系统提示词字符串
        """
        prompt = """你是一个地址解析专家，负责将用户输入的地址信息解析为结构化的数据。

## 解析要求

### 一级地址（first_level_address）
- 精确到具体的大楼信息
- 例如：输入"上海市虹桥路1号港汇广场3楼NIKE"，一级地址应为"上海市徐汇区虹桥路1号上海港汇广场"

### 二级地址（second_level_address）
- 通过AI分析，精确到具体的门牌、楼层、门店等更细的颗粒度
- 例如：输入"上海市虹桥路1号港汇广场3楼NIKE"，二级地址应为"上海市徐汇区虹桥路1号上海港汇恒隆广场 3F Nike 门店"

### 地理信息提取
- **location**: 经纬度信息，格式为"经度,纬度"（如：121.123456,31.123456）
- **country**: 国家（如：中国）
- **province**: 省份（如：上海市）
- **city**: 城市（如：上海市）
- **district**: 区（如：徐汇区）
- **street**: 街道（如：虹桥路1号）
- **category**: 类别（商圈、住宅、学校、写字楼等，如果能够识别的话）

## 使用工具
- 如果如果有需要调用以下工具进行调用,尽可能减少调用次数.
1. **maps_geo**: 如果地址信息不完整或需要获取经纬度，使用该工具获取地理编码信息.
2. **maps_text_search**: 如果需要搜索POI信息，使用该工具进行搜索
- 如果没有提供工具结果，使用你的内置知识解析

## 输出要求
请严格按照 JSON Schema 输出结果，确保 JSON 语法完全正确,每次都响应结构化的数据。
"""
        return prompt

    @staticmethod
    async def _fetch_geocoding(address: str) -> Optional[str]:
        """
        预先调用高德地图工具获取地理信息原始结果

        同时调用 maps_geo 和 maps_text_search 各一次，提高精度
        直接返回原始文本，让 LLM 自己解析，避免依赖返回格式

        Args:
            address: 地址字符串

        Returns:
            工具返回的原始文本，包含地理信息。如果失败返回 None
        """
        from app.tools.mcp_clients import create_gaode_mcp_client

        try:
            # 创建 MCP 客户端
            client = create_gaode_mcp_client()

            raw_results = []

            # 步骤1: 调用 maps_geo 获取地理编码
            logger.info(f"[地址解析] 预先调用 maps_geo: {address}")
            try:
                # geo_result = await client.call_tool(
                #     "maps_geo",
                #     arguments={"address": address}
                # )
                # 获取可调用的函数对象
                func_maps_geo = await client.get_callable_function("maps_geo",wrap_tool_result= True)
                # geo_params = {"address": address}
                geo_result = await func_maps_geo(address= address)

                logger.info(f"[地址解析] maps_geo 返回: {geo_result}")
                if geo_result:
                    # 直接转换为文本，让 LLM 解析
                    raw_results.append(f"## maps_geo 工具返回结果\n{str(geo_result)}\n")
            except Exception as e:
                logger.warning(f"[地址解析] maps_geo 调用失败: {str(e)}")

            # 步骤2: 调用 maps_text_search 搜索 POI 信息
            logger.info(f"[地址解析] 预先调用 maps_text_search: {address}")
            try:

                text_search_params = {"keywords": address}
                search_result = await client.get_callable_function(keywords= address)

                logger.info(f"[地址解析] maps_text_search 返回: {search_result}")
                if search_result:
                    # 直接转换为文本，让 LLM 解析
                    raw_results.append(f"## maps_text_search 工具返回结果\n{str(search_result)}\n")
            except Exception as e:
                logger.warning(f"[地址解析] maps_text_search 调用失败: {str(e)}")

            # 如果至少有一个工具返回了信息，返回原始结果
            if raw_results:
                combined = "\n".join(raw_results)
                logger.info(f"[地址解析] 合并后的原始结果: {combined[:500]}...")
                return combined
            else:
                return None

        except Exception as e:
            logger.warning(f"[地址解析] 地理信息获取失败，将使用 LLM 推理: {str(e)}")
            return None

    @staticmethod
    async def parse_address_detail(address: str) -> Dict:
        """
        地址详情解析 (使用 AgentScope ReActAgent)

        将原始地址解析为结构化的地址信息

        Args:
            address: 原始地址信息

        Returns:
            包含 success, message, result 的字典
        """
        logger.info(f"[地址解析] 原始地址: {address}")

        # 获取 API Key
        settings = get_settings()
        api_key = settings.DASHSCOPE_API_KEY

        # import agentscope
        # agentscope.init(studio_url="http://localhost:3000")

        # 步骤1: 预先调用工具获取地理信息原始结果（避免 Agent 反复调用）暂时给个false
        geo_raw_result = None # await AddressService._fetch_geocoding(address)

        # 步骤2: 构建系统提示词
        sys_prompt = AddressService._build_address_parse_prompt()
        logger.info(f"[地址解析] 系统提示词长度: {len(sys_prompt)} 字符，已预先获取地理信息: {geo_raw_result is not None}")

        # 步骤3: 构建 user_prompt，如果有工具结果则注入
        if geo_raw_result:
            user_prompt = f"""请解析以下地址信息，返回结构化的数据：

## 原始地址
{address}

## 高德地图工具返回结果（已预先获取）
{geo_raw_result}

请基于上述原始地址和高德地图工具返回结果，输出结构化结果。"""
        else:
            user_prompt = f"""请解析以下地址信息，返回结构化的数据：

## 原始地址
{address}

请使用你的内置知识解析地址，输出结构化结果。"""

        # 步骤4: 初始化 DashScope 模型
        model = DashScopeChatModel(
            model_name="qwen-plus",
            api_key=api_key,
            stream=False,
            enable_thinking=False,
        )
        # 创建 Toolkit
        toolkit = await create_fresh_toolkit()
        # 步骤5: 创建ReActAgent（
        agent = ReActAgent(
            name="address_parse_agent",
            sys_prompt=sys_prompt,
            model=model,
            formatter=DashScopeChatFormatter(),
            toolkit=toolkit,
        )

        try:
            # 调用 ReActAgent
            logger.info(f"[地址解析] 开始调用 ReActAgent 分析...")
            logger.info(f"[地址解析] 用户提示词: {user_prompt[:500]}...")
            logger.info(f"Agent memory before call: {agent.memory.content}")
            msg = Msg("user", user_prompt, "user")
            llm_response = await agent(msg, structured_model=AddressDetailData)

            # 从响应中获取结构化结果
            logger.info(f"[地址解析] 解析结果: {llm_response}")
            result = llm_response.metadata  # AgentScope 将结构化输出放在 metadata 字段中

            return {
                'success': True,
                'message': '地址解析成功',
                'result': result
            }

        except Exception as e:
            logger.error(f"[地址解析] Agent分析失败: {str(e)}", exc_info=True)
            raise ValueError(f"地址解析失败: {str(e)}")
