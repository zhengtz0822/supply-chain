# Supply Chain API

基于 FastAPI + SQLAlchemy 的供应链管理系统 API 项目。

## 项目结构

```
supply-chain/
├── app/
│   ├── core/           # 核心配置
│   │   ├── config.py   # 应用配置
│   │   └── database.py # 数据库配置
│   ├── models/         # 数据库模型
│   │   ├── base.py     # 基础模型
│   │   └── example.py  # 示例模型
│   ├── schemas/        # Pydantic Schema (请求/响应模型)
│   │   └── example.py
│   ├── services/       # 业务逻辑层
│   │   └── example_service.py
│   ├── routers/        # 路由层 (API 端点)
│   │   └── example.py
│   └── main.py         # 应用入口
├── requirements.txt    # 依赖包
├── .env.example        # 环境变量示例
└── README.md
```

## 架构设计

### 分层架构 (便于移植)

1. **routers/** - 路由层
   - 只负责处理 HTTP 请求/响应
   - 参数验证
   - 调用 services 层

2. **services/** - 业务逻辑层
   - 所有业务逻辑
   - 数据处理
   - 调用 models 层

3. **models/** - 数据模型层
   - SQLAlchemy ORM 模型
   - 数据库表结构

4. **schemas/** - 数据传输层
   - Pydantic 模型
   - 请求/响应数据验证

5. **core/** - 核心配置层
   - 数据库连接
   - 应用配置

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改数据库连接等配置
```

### 3. 运行项目

```bash
# 方式一：直接运行
python -m app.main

# 方式二：使用 uvicorn
uvicorn app.main:app --reload

# 方式三：指定 host 和 port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问 API

- API 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc
- API 根路径: http://localhost:8000/

## 数据库配置

### SQLite (默认，适合开发)

```python
DATABASE_URL = "sqlite:///./supply_chain.db"
```

### PostgreSQL

```bash
pip install psycopg2-binary
```

```python
DATABASE_URL = "postgresql://username:password@localhost:5432/dbname"
```

### MySQL

```bash
pip install pymysql
```

```python
DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/dbname"
```

### SQL Server

```bash
pip install pyodbc
```

```python
DATABASE_URL = "mssql+pyodbc://username:password@server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server"
```

### Oracle

```bash
pip install cx_Oracle
```

```python
DATABASE_URL = "oracle+cx_oracle://username:password@localhost:1521/?service_name=orcl"
```

## 添加新的 API

### 1. 创建模型 (models/)

```python
# app/models/product.py
from sqlalchemy import Column, String, Float
from app.models.base import BaseModel

class Product(BaseModel):
    __tablename__ = "products"

    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
```

### 2. 创建 Schema (schemas/)

```python
# app/schemas/product.py
from pydantic import BaseModel

class ProductBase(BaseModel):
    name: str
    price: float

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True
```

### 3. 创建服务层 (services/)

```python
# app/services/product_service.py
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductService:
    @staticmethod
    def create(db: Session, obj_in: ProductCreate) -> Product:
        db_obj = Product(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

### 4. 创建路由 (routers/)

```python
# app/routers/product.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=ProductResponse)
def create_product(obj_in: ProductCreate, db: Session = Depends(get_db)):
    return ProductService.create(db, obj_in)
```

### 5. 注册路由 (main.py)

```python
from app.routers import product

app.include_router(product.router, prefix="/api/v1")
```

## 开发建议

1. **保持分层清晰**: routers → services → models
2. **业务逻辑放在 services 层**: 不要在 routers 中写业务逻辑
3. **使用 Pydantic 验证**: 所有输入输出都用 schemas 定义
4. **错误处理**: 在 services 层抛出异常，routers 层转换为 HTTP 响应

## 移植到其他项目

由于采用分层架构，你可以轻松地将任何模块移植到其他项目：

1. 复制 `models/xxx.py` - 数据模型
2. 复制 `schemas/xxx.py` - 数据传输对象
3. 复制 `services/xxx_service.py` - 业务逻辑
4. 复制 `routers/xxx.py` - API 路由

每个文件都是独立的，只需确保导入路径正确即可。
