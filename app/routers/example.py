from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.example import ExampleCreate, ExampleUpdate, ExampleResponse, ExampleListResponse
from app.services.example_service import ExampleService

router = APIRouter(prefix="/examples", tags=["examples"])


@router.get("", response_model=ExampleListResponse, summary="获取所有示例")
def get_examples(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    is_active: Optional[bool] = Query(None, description="筛选是否启用"),
    db: Session = Depends(get_db),
):
    """
    获取所有示例数据，支持分页和筛选
    """
    items, total = ExampleService.get_all(db, skip=skip, limit=limit, is_active=is_active)
    return ExampleListResponse(total=total, items=items)


@router.get("/{example_id}", response_model=ExampleResponse, summary="获取单个示例")
def get_example(example_id: int, db: Session = Depends(get_db)):
    """
    根据 ID 获取单个示例数据
    """
    item = ExampleService.get_by_id(db, example_id)
    if not item:
        raise HTTPException(status_code=404, detail="Example not found")
    return item


@router.post("", response_model=ExampleResponse, status_code=201, summary="创建示例")
def create_example(obj_in: ExampleCreate, db: Session = Depends(get_db)):
    """
    创建新的示例数据
    """
    try:
        return ExampleService.create(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{example_id}", response_model=ExampleResponse, summary="更新示例")
def update_example(example_id: int, obj_in: ExampleUpdate, db: Session = Depends(get_db)):
    """
    更新示例数据（仅更新提供的字段）
    """
    item = ExampleService.update(db, example_id, obj_in)
    if not item:
        raise HTTPException(status_code=404, detail="Example not found")
    return item


@router.delete("/{example_id}", status_code=204, summary="删除示例")
def delete_example(example_id: int, db: Session = Depends(get_db)):
    """
    物理删除示例数据
    """
    if not ExampleService.delete(db, example_id):
        raise HTTPException(status_code=404, detail="Example not found")


@router.patch("/{example_id}/deactivate", response_model=ExampleResponse, summary="停用示例")
def deactivate_example(example_id: int, db: Session = Depends(get_db)):
    """
    软删除/停用示例数据
    """
    item = ExampleService.soft_delete(db, example_id)
    if not item:
        raise HTTPException(status_code=404, detail="Example not found")
    return item
