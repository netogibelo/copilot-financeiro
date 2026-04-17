from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import os
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models import Import, Account, Transaction, CategoryLearning
from app.services.import_service import parse_file
from app.services.categorization import CategorizationService

router = APIRouter()

ALLOWED_EXTENSIONS = {".ofx", ".ofc", ".xlsx", ".xls", ".csv", ".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    account_id: str = Form(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload e processa extrato bancário."""

    # Validate file
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Verify account
    acc_result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    if not acc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    saved_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, saved_filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # Create import record
    imp = Import(
        user_id=current_user.id,
        account_id=account_id,
        filename=filename,
        status="processing",
        started_at=datetime.now(timezone.utc),
    )
    db.add(imp)
    await db.flush()
    import_id = imp.id

    # Process synchronously for now (Celery async in prod)
    try:
        transactions_data, file_type = parse_file(content, filename)
        imp.file_type = file_type
        imp.total_transactions = len(transactions_data)

        if not transactions_data:
            imp.status = "completed"
            imp.completed_at = datetime.now(timezone.utc)
            await db.flush()
            return {
                "import_id": import_id,
                "status": "completed",
                "total": 0,
                "imported": 0,
                "message": "Nenhuma transação encontrada no arquivo",
            }

        # Categorize and save
        cat_service = CategorizationService(db, current_user.id)
        imported = 0
        duplicates = 0
        previews = []

        for t_data in transactions_data[:200]:  # Limit for sync processing
            # Check duplicate
            existing = await db.execute(
                select(Transaction).where(
                    Transaction.user_id == current_user.id,
                    Transaction.account_id == account_id,
                    Transaction.date == t_data["date"],
                    Transaction.amount == t_data["amount"],
                    Transaction.description == t_data["description"],
                )
            )
            if existing.scalars().first():
                duplicates += 1
                continue

            # Auto-categorize
            suggestion = await cat_service.suggest_category(t_data["description"])

            # Detect installment
            installment_info = await cat_service.detect_installments(t_data["description"])

            t = Transaction(
                user_id=current_user.id,
                account_id=account_id,
                category_id=suggestion.get("category_id"),
                type=t_data["type"],
                description=t_data["description"],
                original_description=t_data.get("original_description"),
                amount=t_data["amount"],
                date=t_data["date"],
                is_paid=True,
                import_id=import_id,
                installment_current=installment_info["current"] if installment_info else None,
                installment_total=installment_info["total"] if installment_info else None,
            )
            db.add(t)
            imported += 1

            previews.append({
                "date": str(t_data["date"]),
                "description": t_data["description"],
                "amount": t_data["amount"],
                "type": t_data["type"],
                "category": suggestion.get("category_name"),
                "needs_review": suggestion.get("needs_review", False),
            })

        imp.imported_transactions = imported
        imp.duplicate_transactions = duplicates
        imp.status = "completed"
        imp.completed_at = datetime.now(timezone.utc)

        return {
            "import_id": import_id,
            "status": "completed",
            "total": len(transactions_data),
            "imported": imported,
            "duplicates": duplicates,
            "needs_review": sum(1 for p in previews if p["needs_review"]),
            "preview": previews[:20],
        }

    except Exception as e:
        imp.status = "failed"
        imp.error_message = str(e)
        imp.completed_at = datetime.now(timezone.utc)
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


@router.get("/history")
async def list_imports(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Import)
        .where(Import.user_id == current_user.id)
        .order_by(Import.created_at.desc())
        .limit(50)
    )
    imports = result.scalars().all()
    return [
        {
            "id": i.id,
            "filename": i.filename,
            "file_type": i.file_type,
            "status": i.status,
            "total_transactions": i.total_transactions,
            "imported_transactions": i.imported_transactions,
            "duplicate_transactions": i.duplicate_transactions,
            "error_message": i.error_message,
            "created_at": i.created_at.isoformat(),
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in imports
    ]
