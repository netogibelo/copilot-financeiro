from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Category

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str
    type: str  # receita | despesa | investimento | transferencia
    icon: str = "tag"
    color: str = "#6366f1"
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.get("")
async def list_categories(
    type: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista categorias do usuário + categorias do sistema."""
    filters = [
        or_(Category.user_id == current_user.id, Category.is_system == True)
    ]
    if type:
        filters.append(Category.type == type)

    result = await db.execute(
        select(Category)
        .where(*filters)
        .order_by(Category.is_system.desc(), Category.name)
    )
    categories = result.scalars().all()
    return [_serialize(c) for c in categories]


@router.post("", status_code=201)
async def create_category(
    data: CategoryCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    existing = await db.execute(
        select(Category).where(
            or_(Category.user_id == current_user.id, Category.is_system == True),
            Category.name == data.name,
            Category.type == data.type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Categoria já existe com este nome e tipo")

    cat = Category(user_id=current_user.id, **data.model_dump())
    db.add(cat)
    await db.flush()
    return _serialize(cat)


@router.patch("/{category_id}")
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == current_user.id,
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou é do sistema")

    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    return _serialize(cat)


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == current_user.id,
            Category.is_system == False,
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou não pode ser excluída")

    await db.delete(cat)
    return {"message": "Categoria excluída"}


def _serialize(c: Category) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "type": c.type,
        "icon": c.icon,
        "color": c.color,
        "parent_id": c.parent_id,
        "is_system": c.is_system,
        "user_id": c.user_id,
    }
