# =====================================================
# accounts.py
# =====================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, Transaction

router = APIRouter()

class AccountCreate(BaseModel):
    name: str
    type: str
    bank_name: Optional[str] = None
    balance: float = 0
    credit_limit: Optional[float] = None
    closing_day: Optional[int] = None
    due_day: Optional[int] = None
    color: str = "#6366f1"
    icon: str = "wallet"
    include_in_total: bool = True

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    closing_day: Optional[int] = None
    due_day: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    include_in_total: Optional[bool] = None

@router.get("")
async def list_accounts(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.user_id == current_user.id, Account.is_active == True).order_by(Account.name))
    accounts = result.scalars().all()
    total_balance = sum(a.balance for a in accounts if a.include_in_total)
    return {"accounts": [_serialize_account(a) for a in accounts], "total_balance": float(total_balance)}

@router.post("", status_code=201)
async def create_account(data: AccountCreate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = Account(user_id=current_user.id, **data.model_dump())
    db.add(account)
    await db.flush()
    return _serialize_account(account)

@router.patch("/{account_id}")
async def update_account(account_id: str, data: AccountUpdate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id, Account.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(account, k, v)
    return _serialize_account(account)

@router.delete("/{account_id}")
async def delete_account(account_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id, Account.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    account.is_active = False
    return {"message": "Conta desativada"}

def _serialize_account(a):
    return {"id": a.id, "name": a.name, "type": a.type, "bank_name": a.bank_name, "balance": float(a.balance), "credit_limit": float(a.credit_limit) if a.credit_limit else None, "closing_day": a.closing_day, "due_day": a.due_day, "color": a.color, "icon": a.icon, "is_active": a.is_active, "include_in_total": a.include_in_total, "created_at": a.created_at.isoformat()}
