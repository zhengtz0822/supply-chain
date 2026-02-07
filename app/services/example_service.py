from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.example import Example
from app.schemas.example import ExampleCreate, ExampleUpdate


class ExampleService:
    """
    Example 业务逻辑服务层
    所有业务逻辑放在这里，路由层只负责处理 HTTP 请求/响应
    """

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> tuple[List[Example], int]:
        """
        获取所有 Example
        返回: (列表, 总数)
        """
        query = db.query(Example)

        if is_active is not None:
            query = query.filter(Example.is_active == is_active)

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def get_by_id(db: Session, example_id: int) -> Optional[Example]:
        """根据 ID 获取 Example"""
        return db.query(Example).filter(Example.id == example_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[Example]:
        """根据编码获取 Example"""
        return db.query(Example).filter(Example.code == code).first()

    @staticmethod
    def create(db: Session, obj_in: ExampleCreate) -> Example:
        """创建新的 Example"""
        # 检查编码是否已存在
        existing = ExampleService.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Code '{obj_in.code}' already exists")

        db_obj = Example(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def update(db: Session, example_id: int, obj_in: ExampleUpdate) -> Optional[Example]:
        """更新 Example"""
        db_obj = ExampleService.get_by_id(db, example_id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, example_id: int) -> bool:
        """删除 Example"""
        db_obj = ExampleService.get_by_id(db, example_id)
        if not db_obj:
            return False

        db.delete(db_obj)
        db.commit()
        return True

    @staticmethod
    def soft_delete(db: Session, example_id: int) -> Optional[Example]:
        """软删除 Example (设置 is_active = False)"""
        db_obj = ExampleService.get_by_id(db, example_id)
        if not db_obj:
            return None

        db_obj.is_active = False
        db.commit()
        db.refresh(db_obj)
        return db_obj
