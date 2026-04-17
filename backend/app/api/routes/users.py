# users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash

router = APIRouter()

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email, "role": current_user.role, "avatar_url": current_user.avatar_url, "is_email_verified": current_user.is_email_verified, "created_at": current_user.created_at.isoformat()}

@router.patch("/me")
async def update_me(data: UserUpdate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(current_user, k, v)
    await db.flush()
    return {"message": "Perfil atualizado"}

@router.post("/me/change-password")
async def change_password(data: PasswordChange, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.core.security import verify_password
    if not current_user.password_hash or not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 8 caracteres")
    current_user.password_hash = get_password_hash(data.new_password)
    await db.flush()
    return {"message": "Senha alterada com sucesso"}
