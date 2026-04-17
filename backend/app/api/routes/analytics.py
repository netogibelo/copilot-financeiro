from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, datetime
from calendar import monthrange

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Transaction, Category, Account

router = APIRouter()
reports_router = APIRouter()


@router.post("/track")
async def track_event(
    event_type: str,
    page: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Track usage analytics."""
    from app.models import AuditLog
    log = AuditLog(user_id=current_user.id, action=event_type, entity_type="page", details={"page": page})
    db.add(log)
    return {"tracked": True}


@router.get("/monthly-comparison")
async def monthly_comparison(
    months: int = Query(default=6, ge=1, le=24),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Comparação mensal de receitas vs despesas."""
    today = datetime.now()
    result = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        _, last_day = monthrange(y, m)
        start = date(y, m, 1)
        end = date(y, m, last_day)

        income = (await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.type == "receita",
                Transaction.date >= start, Transaction.date <= end,
            )
        )).scalar() or 0

        expense = (await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.type == "despesa",
                Transaction.date >= start, Transaction.date <= end,
            )
        )).scalar() or 0

        investment = (await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.type == "investimento",
                Transaction.date >= start, Transaction.date <= end,
            )
        )).scalar() or 0

        result.append({
            "month": m, "year": y,
            "label": f"{m:02d}/{y}",
            "income": float(income),
            "expense": float(expense),
            "investment": float(investment),
            "balance": float(income - expense - investment),
        })

    return result


@router.get("/category-trends")
async def category_trends(
    months: int = Query(default=3, ge=1, le=12),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Identifica categorias com maior crescimento."""
    today = datetime.now()
    trends = {}

    for i in range(months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        _, last_day = monthrange(y, m)
        start = date(y, m, 1)
        end = date(y, m, last_day)

        cat_q = (
            select(Category.name, Category.color, func.sum(Transaction.amount).label("total"))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == current_user.id,
                Transaction.type == "despesa",
                Transaction.date >= start,
                Transaction.date <= end,
            )
            .group_by(Category.name, Category.color)
        )
        result = await db.execute(cat_q)
        for row in result.all():
            trends.setdefault(row.name, {"name": row.name, "color": row.color, "monthly": []})
            trends[row.name]["monthly"].insert(0, {"month": f"{m:02d}/{y}", "total": float(row.total)})

    # Calculate growth rate
    result_list = []
    for name, data in trends.items():
        monthly = data["monthly"]
        if len(monthly) >= 2:
            first = monthly[0]["total"]
            last = monthly[-1]["total"]
            growth = ((last - first) / first * 100) if first > 0 else 0
            data["growth_pct"] = round(growth, 1)
            data["avg_monthly"] = round(sum(m["total"] for m in monthly) / len(monthly), 2)
            result_list.append(data)

    result_list.sort(key=lambda x: x.get("growth_pct", 0), reverse=True)
    return result_list[:10]


# =====================================================
# REPORTS ROUTER
# =====================================================

@reports_router.get("/cashflow-statement")
async def cashflow_statement(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Demonstrativo de fluxo de caixa."""
    filters = [
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ]

    total_income = (await db.execute(
        select(func.sum(Transaction.amount)).where(*filters, Transaction.type == "receita")
    )).scalar() or 0

    total_expense = (await db.execute(
        select(func.sum(Transaction.amount)).where(*filters, Transaction.type == "despesa")
    )).scalar() or 0

    total_investment = (await db.execute(
        select(func.sum(Transaction.amount)).where(*filters, Transaction.type == "investimento")
    )).scalar() or 0

    cat_income_q = (
        select(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(*filters, Transaction.type == "receita")
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )
    income_by_cat = [(r.name, float(r.total)) for r in (await db.execute(cat_income_q)).all()]

    cat_expense_q = (
        select(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(*filters, Transaction.type == "despesa")
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )
    expense_by_cat = [(r.name, float(r.total)) for r in (await db.execute(cat_expense_q)).all()]

    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "summary": {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "total_investment": float(total_investment),
            "net_result": float(total_income - total_expense - total_investment),
            "savings_rate": round((total_income - total_expense) / total_income * 100, 1) if total_income > 0 else 0,
        },
        "income_by_category": [{"name": n, "total": t} for n, t in income_by_cat],
        "expense_by_category": [{"name": n, "total": t} for n, t in expense_by_cat],
    }
