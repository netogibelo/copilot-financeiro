from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, timedelta
from calendar import monthrange
import statistics

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Transaction, CashflowPrediction, Account, SubscriptionDetected, InstallmentDetected

router = APIRouter()


@router.get("/predict")
async def predict_cashflow(
    days: int = Query(default=90, ge=7, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Prevê fluxo de caixa para os próximos N dias.
    Algoritmo:
    1. Calcula médias mensais histórias (6 meses)
    2. Projeta receitas e despesas esperadas
    3. Adiciona assinaturas e parcelamentos pendentes
    4. Gera alerta se saldo ficar negativo
    """
    today = date.today()
    six_months_ago = today - timedelta(days=180)

    # Historical monthly averages
    monthly_data = {}
    for i in range(6):
        m_date = today - timedelta(days=30 * i)
        month, year = m_date.month, m_date.year
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)

        income_q = await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.type == "receita",
                Transaction.date >= start,
                Transaction.date <= end,
            )
        )
        expense_q = await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.type == "despesa",
                Transaction.date >= start,
                Transaction.date <= end,
            )
        )
        monthly_data[f"{year}-{month:02d}"] = {
            "income": float(income_q.scalar() or 0),
            "expense": float(expense_q.scalar() or 0),
        }

    values = list(monthly_data.values())
    incomes = [v["income"] for v in values if v["income"] > 0]
    expenses = [v["expense"] for v in values if v["expense"] > 0]

    avg_monthly_income = statistics.mean(incomes) if incomes else 0
    avg_monthly_expense = statistics.mean(expenses) if expenses else 0
    avg_daily_income = avg_monthly_income / 30
    avg_daily_expense = avg_monthly_expense / 30

    # Get current balance
    acc_result = await db.execute(
        select(func.sum(Account.balance)).where(
            Account.user_id == current_user.id,
            Account.is_active == True,
            Account.include_in_total == True,
        )
    )
    current_balance = float(acc_result.scalar() or 0)

    # Active subscriptions (upcoming)
    subs_result = await db.execute(
        select(SubscriptionDetected).where(
            SubscriptionDetected.user_id == current_user.id,
            SubscriptionDetected.status == "active",
        )
    )
    subscriptions = subs_result.scalars().all()

    # Pending installments
    inst_result = await db.execute(
        select(InstallmentDetected).where(
            InstallmentDetected.user_id == current_user.id,
            InstallmentDetected.remaining_installments > 0,
        )
    )
    installments = inst_result.scalars().all()

    # Build daily projection
    projections = []
    running_balance = current_balance
    negative_day = None
    
    subscription_map = {}
    for sub in subscriptions:
        if sub.next_expected_at:
            d = sub.next_expected_at
            while d <= today + timedelta(days=days):
                key = str(d)
                subscription_map.setdefault(key, 0)
                subscription_map[key] += float(sub.amount)
                d = d + timedelta(days=sub.frequency_days)

    for day_offset in range(days):
        proj_date = today + timedelta(days=day_offset)
        date_key = str(proj_date)
        
        daily_income = avg_daily_income
        daily_expense = avg_daily_expense
        
        # Add subscriptions
        daily_expense += subscription_map.get(date_key, 0)
        
        # Add installments (distributed monthly)
        for inst in installments:
            if inst.end_date and proj_date <= inst.end_date:
                daily_expense += float(inst.installment_amount) / 30
        
        running_balance += daily_income - daily_expense
        
        if running_balance < 0 and negative_day is None:
            negative_day = day_offset
        
        projections.append({
            "date": date_key,
            "projected_income": round(daily_income, 2),
            "projected_expense": round(daily_expense, 2),
            "projected_balance": round(running_balance, 2),
        })

    # Save predictions to DB (batch upsert simplified)
    for proj in projections[::7]:  # Save weekly
        existing = await db.execute(
            select(CashflowPrediction).where(
                CashflowPrediction.user_id == current_user.id,
                CashflowPrediction.prediction_date == proj["date"],
            )
        )
        pred = existing.scalar_one_or_none()
        if not pred:
            pred = CashflowPrediction(
                user_id=current_user.id,
                prediction_date=proj["date"],
                predicted_balance=proj["projected_balance"],
                predicted_income=proj["projected_income"],
                predicted_expense=proj["projected_expense"],
                confidence_score=0.75,
                model_version="v1.0",
            )
            db.add(pred)

    # Alerts
    alerts = []
    if negative_day is not None:
        alerts.append({
            "type": "danger",
            "message": f"⚠️ Seu saldo ficará negativo em aproximadamente {negative_day} dias se mantiver o ritmo atual.",
        })
    
    expense_ratio = avg_monthly_expense / avg_monthly_income if avg_monthly_income > 0 else 0
    if expense_ratio > 0.9:
        alerts.append({
            "type": "warning",
            "message": f"🔴 Suas despesas representam {expense_ratio*100:.0f}% da sua renda. Considere reduzir gastos.",
        })
    elif expense_ratio > 0.7:
        alerts.append({
            "type": "warning",
            "message": f"🟡 Suas despesas estão em {expense_ratio*100:.0f}% da renda. Fique atento ao orçamento.",
        })
    else:
        alerts.append({
            "type": "success",
            "message": f"✅ Ótimo! Suas despesas estão em {expense_ratio*100:.0f}% da renda. Continue assim!",
        })

    sub_total = sum(float(s.amount) for s in subscriptions)
    if sub_total > avg_monthly_income * 0.15:
        alerts.append({
            "type": "warning",
            "message": f"📺 Assinaturas consomem R$ {sub_total:,.2f}/mês ({sub_total/avg_monthly_income*100:.0f}% da renda). Revise o que usa menos.",
        })

    return {
        "current_balance": current_balance,
        "avg_monthly_income": round(avg_monthly_income, 2),
        "avg_monthly_expense": round(avg_monthly_expense, 2),
        "projections": projections,
        "alerts": alerts,
        "days_until_negative": negative_day,
        "potential_monthly_savings": max(0, round(avg_monthly_income - avg_monthly_expense, 2)),
    }
