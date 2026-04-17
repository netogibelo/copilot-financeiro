from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_admin, get_password_hash
from app.models import User, Account, Category, Transaction, Import, AuditLog, SubscriptionDetected, InstallmentDetected

router = APIRouter()


async def log_action(db, admin_id: str, action: str, entity_type: str = None, entity_id: str = None, details: dict = None):
    log = AuditLog(admin_id=admin_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
    db.add(log)


# =====================================================
# DASHBOARD STATS
# =====================================================

@router.get("/stats")
async def admin_stats(admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_users = (await db.execute(select(func.count()).select_from(User).where(User.is_active == True))).scalar()
    total_txns = (await db.execute(select(func.count()).select_from(Transaction))).scalar()
    total_imports = (await db.execute(select(func.count()).select_from(Import))).scalar()
    total_accounts = (await db.execute(select(func.count()).select_from(Account))).scalar()
    total_subs = (await db.execute(select(func.count()).select_from(SubscriptionDetected))).scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_transactions": total_txns,
        "total_imports": total_imports,
        "total_accounts": total_accounts,
        "total_subscriptions": total_subs,
    }


# =====================================================
# USERS
# =====================================================

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if search:
        from sqlalchemy import or_
        filters.append(or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    total = (await db.execute(select(func.count()).select_from(User).where(*filters))).scalar()
    result = await db.execute(
        select(User).where(*filters)
        .order_by(User.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    users = result.scalars().all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "data": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "is_email_verified": u.is_email_verified, "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None, "created_at": u.created_at.isoformat()} for u in users]
    }


@router.patch("/users/{user_id}/block")
async def block_user(user_id: str, admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Não é possível bloquear sua própria conta")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = not user.is_active
    action = "user_blocked" if not user.is_active else "user_unblocked"
    await log_action(db, admin.id, action, "user", user_id)
    return {"message": f"Usuário {'bloqueado' if not user.is_active else 'desbloqueado'}", "is_active": user.is_active}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    import secrets, string
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    temp_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    user.password_hash = get_password_hash(temp_password)
    await log_action(db, admin.id, "user_password_reset", "user", user_id)
    return {"message": "Senha redefinida", "temp_password": temp_password}


@router.patch("/users/{user_id}/role")
async def change_role(user_id: str, role: str = Query(..., regex="^(user|admin)$"), admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    old_role = user.role
    user.role = role
    await log_action(db, admin.id, "user_role_changed", "user", user_id, {"old_role": old_role, "new_role": role})
    return {"message": f"Role alterado para {role}"}


# =====================================================
# TRANSACTIONS (admin view)
# =====================================================

@router.get("/transactions")
async def admin_list_transactions(
    user_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 30,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, or_
    filters = []
    if user_id:
        filters.append(Transaction.user_id == user_id)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))
    
    total = (await db.execute(select(func.count()).select_from(Transaction).where(*filters))).scalar()
    result = await db.execute(
        select(Transaction).where(*filters)
        .order_by(Transaction.date.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    txns = result.scalars().all()
    return {
        "total": total, "page": page,
        "data": [{"id": t.id, "user_id": t.user_id, "description": t.description, "amount": float(t.amount), "type": t.type, "date": str(t.date), "category_id": t.category_id} for t in txns]
    }


@router.delete("/transactions/{transaction_id}")
async def admin_delete_transaction(transaction_id: str, admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    await db.delete(t)
    await log_action(db, admin.id, "transaction_deleted", "transaction", transaction_id)
    return {"message": "Transação excluída"}


# =====================================================
# CATEGORIES (admin)
# =====================================================

@router.get("/categories")
async def admin_list_categories(admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.is_system.desc(), Category.name))
    cats = result.scalars().all()
    return [{"id": c.id, "name": c.name, "type": c.type, "icon": c.icon, "color": c.color, "is_system": c.is_system, "user_id": c.user_id} for c in cats]


# =====================================================
# AUDIT LOGS
# =====================================================

@router.get("/audit-logs")
async def admin_audit_logs(
    page: int = 1,
    per_page: int = 30,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar()
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    logs = result.scalars().all()
    return {
        "total": total,
        "data": [{"id": l.id, "admin_id": l.admin_id, "action": l.action, "entity_type": l.entity_type, "entity_id": str(l.entity_id) if l.entity_id else None, "details": l.details, "created_at": l.created_at.isoformat()} for l in logs]
    }


# =====================================================
# IMPORTS (admin)
# =====================================================

@router.get("/imports")
async def admin_list_imports(
    user_id: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if user_id:
        filters.append(Import.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(Import).where(*filters))).scalar()
    result = await db.execute(
        select(Import).where(*filters).order_by(Import.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    )
    imports = result.scalars().all()
    return {
        "total": total,
        "data": [{"id": i.id, "user_id": i.user_id, "filename": i.filename, "file_type": i.file_type, "status": i.status, "total_transactions": i.total_transactions, "imported_transactions": i.imported_transactions, "created_at": i.created_at.isoformat()} for i in imports]
    }
