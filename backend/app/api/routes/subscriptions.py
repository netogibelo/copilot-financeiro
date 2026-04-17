from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update as sql_update
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from calendar import monthrange

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    SubscriptionDetected, InstallmentDetected, CashflowPrediction,
    Transaction, Account
)

# =====================================================
# SUBSCRIPTIONS
# =====================================================
router = APIRouter()


@router.get("")
async def list_subscriptions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubscriptionDetected)
        .where(SubscriptionDetected.user_id == current_user.id)
        .order_by(SubscriptionDetected.amount.desc())
    )
    subs = result.scalars().all()
    total = sum(s.amount for s in subs if s.status == "active")
    return {
        "subscriptions": [_serialize_sub(s) for s in subs],
        "total_monthly": float(total),
    }


@router.post("/detect")
async def detect_subscriptions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Roda detecção de assinaturas nas transações do usuário."""
    from app.services.categorization import CategorizationService
    import statistics
    from collections import defaultdict

    # Get last 6 months of transactions
    six_months_ago = date.today() - timedelta(days=180)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "despesa",
            Transaction.date >= six_months_ago,
        ).order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {"detected": 0, "message": "Sem transações suficientes para análise"}

    # Group by normalized description
    groups = defaultdict(list)
    for t in transactions:
        key = t.description.strip().upper()[:50]
        groups[key].append(t)

    detected = 0
    for key, group in groups.items():
        if len(group) < 2:
            continue

        amounts = [float(t.amount) for t in group]
        dates = sorted([t.date for t in group])

        # Consistent amounts (5% tolerance)
        if len(amounts) > 1 and (max(amounts) - min(amounts)) > max(amounts) * 0.1:
            continue

        # Calculate intervals
        if len(dates) >= 2:
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            avg_interval = sum(intervals) / len(intervals)

            # Classify
            freq = None
            if 25 <= avg_interval <= 35:
                freq = 30
            elif 6 <= avg_interval <= 8:
                freq = 7
            elif 360 <= avg_interval <= 370:
                freq = 365
            else:
                continue

            # Check if already detected
            existing = await db.execute(
                select(SubscriptionDetected).where(
                    SubscriptionDetected.user_id == current_user.id,
                    SubscriptionDetected.pattern_keyword == key[:255],
                )
            )
            sub = existing.scalar_one_or_none()

            avg_amount = sum(amounts) / len(amounts)
            next_date = dates[-1] + timedelta(days=freq)

            if sub:
                sub.amount = avg_amount
                sub.last_detected_at = dates[-1]
                sub.next_expected_at = next_date
                sub.transaction_ids = [str(t.id) for t in group]
                if sub.status == "suspected":
                    sub.status = "active"
            else:
                sub = SubscriptionDetected(
                    user_id=current_user.id,
                    name=group[0].description[:255],
                    amount=avg_amount,
                    frequency_days=freq,
                    last_detected_at=dates[-1],
                    next_expected_at=next_date,
                    status="active" if len(group) >= 3 else "suspected",
                    pattern_keyword=key[:255],
                    transaction_ids=[str(t.id) for t in group],
                )
                db.add(sub)
                detected += 1

    await db.flush()
    return {"detected": detected, "message": f"{detected} nova(s) assinatura(s) detectada(s)"}


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    status: str = Query(..., regex="^(active|cancelled|suspected)$"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubscriptionDetected).where(
            SubscriptionDetected.id == subscription_id,
            SubscriptionDetected.user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    sub.status = status
    return {"message": "Assinatura atualizada"}


def _serialize_sub(s: SubscriptionDetected) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "amount": float(s.amount),
        "frequency_days": s.frequency_days,
        "frequency_label": "Mensal" if s.frequency_days == 30 else ("Semanal" if s.frequency_days == 7 else "Anual"),
        "last_detected_at": str(s.last_detected_at) if s.last_detected_at else None,
        "next_expected_at": str(s.next_expected_at) if s.next_expected_at else None,
        "status": s.status,
        "category_id": s.category_id,
    }
