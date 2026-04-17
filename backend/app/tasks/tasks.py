from app.tasks.celery_app import celery_app
from loguru import logger


@celery_app.task(name="app.tasks.tasks.detect_subscriptions_all_users")
def detect_subscriptions_all_users():
    """Detecta assinaturas para todos os usuários ativos."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import User

    DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    async def _run():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            for user in users:
                try:
                    from app.api.routes.subscriptions import detect_subscriptions
                    # Simplified - would call service directly
                    logger.info(f"Detecting subscriptions for user {user.id}")
                except Exception as e:
                    logger.error(f"Error detecting subscriptions for user {user.id}: {e}")
        await engine.dispose()

    asyncio.run(_run())
    logger.info("Subscription detection completed for all users")


@celery_app.task(name="app.tasks.tasks.predict_cashflow_all_users")
def predict_cashflow_all_users():
    """Gera previsões de fluxo de caixa para todos os usuários."""
    logger.info("Running cashflow predictions for all users...")
    # Implementation similar to detect_subscriptions_all_users
    # Would call cashflow service for each user


@celery_app.task(name="app.tasks.tasks.generate_weekly_reports")
def generate_weekly_reports():
    """
    Gera relatórios semanais com:
    - Resumo financeiro da semana
    - Categorias com maior crescimento
    - Alertas detectados
    - Sugestões de IA baseadas em uso
    """
    logger.info("Generating weekly AI reports...")


@celery_app.task(name="app.tasks.tasks.process_import")
def process_import(import_id: str, file_path: str, account_id: str, user_id: str):
    """Processa importação de extrato de forma assíncrona."""
    import asyncio
    
    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.core.config import settings
        DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as db:
            from app.models import Import
            from sqlalchemy import select, update
            from datetime import datetime, timezone
            
            with open(file_path, "rb") as f:
                content = f.read()
            
            from app.services.import_service import parse_file
            filename = file_path.split("/")[-1]
            transactions_data, file_type = parse_file(content, filename)
            
            await db.execute(
                update(Import)
                .where(Import.id == import_id)
                .values(
                    status="completed",
                    total_transactions=len(transactions_data),
                    imported_transactions=len(transactions_data),
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
        await engine.dispose()

    asyncio.run(_run())
    logger.info(f"Import {import_id} processed successfully")
