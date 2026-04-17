from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Transaction, Account, Category, CategoryLearning
from app.services.categorization import CategorizationService

router = APIRouter()


# =====================================================
# SCHEMAS
# =====================================================

class TransactionCreate(BaseModel):
    account_id: str
    category_id: Optional[str] = None
    type: str
    description: str
    amount: float
    date: date
    is_paid: bool = True
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    installment_total: Optional[int] = None
    installment_current: Optional[int] = None
    transfer_account_id: Optional[str] = None


class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[date] = None
    is_paid: Optional[bool] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class CategorySuggestion(BaseModel):
    description: str


# =====================================================
# LIST TRANSACTIONS
# =====================================================

@router.get("")
async def list_transactions(
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    is_paid: Optional[bool] = None,
    page: int = 1,
    per_page: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Transaction.user_id == current_user.id]

    if account_id:
        filters.append(Transaction.account_id == account_id)
    if category_id:
        filters.append(Transaction.category_id == category_id)
    if type:
        filters.append(Transaction.type == type)
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))
    if is_paid is not None:
        filters.append(Transaction.is_paid == is_paid)

    # Count
    count_q = select(func.count()).select_from(Transaction).where(and_(*filters))
    total = (await db.execute(count_q)).scalar()

    # Data
    q = (
        select(Transaction)
        .where(and_(*filters))
        .options(selectinload(Transaction.category), selectinload(Transaction.account))
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    transactions = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "data": [_serialize_transaction(t) for t in transactions],
    }


# =====================================================
# SUMMARY
# =====================================================

@router.get("/summary")
async def get_summary(
    month: int = Query(default=datetime.now().month),
    year: int = Query(default=datetime.now().year),
    account_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    base_filters = [
        Transaction.user_id == current_user.id,
        Transaction.date >= start,
        Transaction.date <= end,
    ]
    if account_id:
        base_filters.append(Transaction.account_id == account_id)

    # Income
    income_q = select(func.sum(Transaction.amount)).where(
        and_(*base_filters, Transaction.type == "receita")
    )
    income = (await db.execute(income_q)).scalar() or 0

    # Expense
    expense_q = select(func.sum(Transaction.amount)).where(
        and_(*base_filters, Transaction.type == "despesa")
    )
    expense = (await db.execute(expense_q)).scalar() or 0

    # Investment
    investment_q = select(func.sum(Transaction.amount)).where(
        and_(*base_filters, Transaction.type == "investimento")
    )
    investment = (await db.execute(investment_q)).scalar() or 0

    # By category (expenses)
    cat_q = (
        select(Category.name, Category.color, Category.icon, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(*base_filters, Transaction.type == "despesa"))
        .group_by(Category.id, Category.name, Category.color, Category.icon)
        .order_by(func.sum(Transaction.amount).desc())
    )
    cat_result = await db.execute(cat_q)
    by_category = [
        {"name": r.name, "color": r.color, "icon": r.icon, "total": float(r.total)}
        for r in cat_result.all()
    ]

    # Daily evolution
    daily_q = (
        select(Transaction.date, func.sum(Transaction.amount).label("total"), Transaction.type)
        .where(and_(*base_filters))
        .group_by(Transaction.date, Transaction.type)
        .order_by(Transaction.date)
    )
    daily_result = await db.execute(daily_q)
    daily_data = {}
    for r in daily_result.all():
        key = str(r.date)
        if key not in daily_data:
            daily_data[key] = {"date": key, "receita": 0, "despesa": 0, "investimento": 0}
        daily_data[key][r.type] = float(r.total)

    return {
        "month": month,
        "year": year,
        "income": float(income),
        "expense": float(expense),
        "investment": float(investment),
        "balance": float(income - expense - investment),
        "by_category": by_category,
        "daily_evolution": sorted(daily_data.values(), key=lambda x: x["date"]),
    }


# =====================================================
# CREATE TRANSACTION
# =====================================================

@router.post("", status_code=201)
async def create_transaction(
    data: TransactionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify account belongs to user
    acc_result = await db.execute(
        select(Account).where(Account.id == data.account_id, Account.user_id == current_user.id)
    )
    if not acc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    transactions = []

    # Handle installments
    if data.installment_total and data.installment_total > 1:
        group_id = str(uuid.uuid4())
        from dateutil.relativedelta import relativedelta
        for i in range(data.installment_current or 1, data.installment_total + 1):
            months_ahead = i - (data.installment_current or 1)
            t_date = data.date + relativedelta(months=months_ahead) if months_ahead > 0 else data.date
            t = Transaction(
                user_id=current_user.id,
                account_id=data.account_id,
                category_id=data.category_id,
                type=data.type,
                description=data.description,
                amount=data.amount,
                date=t_date,
                is_paid=(i == (data.installment_current or 1)),
                notes=data.notes,
                tags=data.tags,
                installment_total=data.installment_total,
                installment_current=i,
                installment_group_id=group_id,
            )
            db.add(t)
            transactions.append(t)
    else:
        t = Transaction(
            user_id=current_user.id,
            **data.model_dump(exclude_none=True),
        )
        db.add(t)
        transactions.append(t)

    await db.flush()

    # Update account balance
    if data.is_paid:
        acc = acc_result.scalar_one()
        if data.type == "receita":
            acc.balance += data.amount
        elif data.type in ("despesa", "investimento"):
            acc.balance -= data.amount

    # Learn category
    if data.category_id:
        await _learn_category(db, current_user.id, data.description, data.category_id)

    return {"message": f"{len(transactions)} lançamento(s) criado(s)", "ids": [t.id for t in transactions]}


# =====================================================
# UPDATE TRANSACTION
# =====================================================

@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(t, field, value)

    # Learn category correction
    if data.category_id:
        await _learn_category(db, current_user.id, t.description, data.category_id)

    return {"message": "Transação atualizada", "id": t.id}


# =====================================================
# DELETE TRANSACTION
# =====================================================

@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    await db.delete(t)
    return {"message": "Transação excluída"}


# =====================================================
# SUGGEST CATEGORY
# =====================================================

@router.post("/suggest-category")
async def suggest_category(
    data: CategorySuggestion,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CategorizationService(db, current_user.id)
    suggestion = await service.suggest_category(data.description)
    return suggestion


# =====================================================
# HELPERS
# =====================================================

def _serialize_transaction(t: Transaction) -> dict:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "account_name": t.account.name if t.account else None,
        "category_id": t.category_id,
        "category_name": t.category.name if t.category else None,
        "category_color": t.category.color if t.category else None,
        "category_icon": t.category.icon if t.category else None,
        "type": t.type,
        "description": t.description,
        "amount": float(t.amount),
        "date": str(t.date),
        "is_paid": t.is_paid,
        "notes": t.notes,
        "tags": t.tags,
        "installment_total": t.installment_total,
        "installment_current": t.installment_current,
        "installment_group_id": t.installment_group_id,
        "created_at": t.created_at.isoformat(),
    }


async def _learn_category(db: AsyncSession, user_id: str, description: str, category_id: str):
    pattern = description.strip().upper()[:200]
    result = await db.execute(
        select(CategoryLearning).where(
            CategoryLearning.user_id == user_id,
            CategoryLearning.pattern == pattern,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.category_id = category_id
        existing.usage_count += 1
        from datetime import datetime, timezone
        existing.last_used_at = datetime.now(timezone.utc)
    else:
        db.add(CategoryLearning(user_id=user_id, pattern=pattern, category_id=category_id))
