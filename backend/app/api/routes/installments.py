from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import InstallmentDetected, Transaction
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

router = APIRouter()


@router.get("")
async def list_installments(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InstallmentDetected)
        .where(InstallmentDetected.user_id == current_user.id)
        .order_by(InstallmentDetected.end_date)
    )
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "description": i.description,
            "total_amount": float(i.total_amount),
            "installment_amount": float(i.installment_amount),
            "total_installments": i.total_installments,
            "paid_installments": i.paid_installments,
            "remaining_installments": i.remaining_installments,
            "start_date": str(i.start_date) if i.start_date else None,
            "end_date": str(i.end_date) if i.end_date else None,
            "remaining_amount": float(i.installment_amount * i.remaining_installments),
        }
        for i in items
    ]


@router.post("/detect")
async def detect_installments(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detecta parcelamentos nas transações."""
    import re

    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.installment_total != None,
        )
    )
    transactions = result.scalars().all()

    # Group by installment_group_id
    from collections import defaultdict
    groups = defaultdict(list)
    for t in transactions:
        if t.installment_group_id:
            groups[str(t.installment_group_id)].append(t)

    created = 0
    for group_id, group_txs in groups.items():
        existing = await db.execute(
            select(InstallmentDetected).where(InstallmentDetected.group_id == group_id)
        )
        if existing.scalar_one_or_none():
            continue

        sorted_txs = sorted(group_txs, key=lambda t: t.installment_current or 0)
        total = sorted_txs[0].installment_total or len(sorted_txs)
        paid = len([t for t in sorted_txs if t.is_paid])
        remaining = total - paid

        inst = InstallmentDetected(
            user_id=current_user.id,
            description=sorted_txs[0].description,
            total_amount=float(sorted_txs[0].amount) * total,
            installment_amount=float(sorted_txs[0].amount),
            total_installments=total,
            paid_installments=paid,
            remaining_installments=remaining,
            start_date=sorted_txs[0].date,
            end_date=sorted_txs[-1].date if len(sorted_txs) > 1 else None,
            category_id=sorted_txs[0].category_id,
            account_id=sorted_txs[0].account_id,
            group_id=group_id,
        )
        db.add(inst)
        created += 1

    await db.flush()
    return {"detected": created}
