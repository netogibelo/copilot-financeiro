"""
Seed inicial - cria admin e dados de exemplo
Executar: python -m app.seed
"""
import asyncio
from sqlalchemy import select
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import get_password_hash
from app.core.config import settings
from app.models import User, Account, Category
import uuid


async def create_admin():
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print(f"✅ Admin já existe: {settings.ADMIN_EMAIL}")
            return

        admin = User(
            name="Administrador",
            email=settings.ADMIN_EMAIL,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            role="admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ Admin criado: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")


async def create_demo_user():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "demo@copilotfinanceiro.com"))
        if result.scalar_one_or_none():
            print("✅ Usuário demo já existe")
            return

        demo = User(
            name="Usuário Demo",
            email="demo@copilotfinanceiro.com",
            password_hash=get_password_hash("Demo@123"),
            role="user",
            is_active=True,
            is_email_verified=True,
        )
        db.add(demo)
        await db.flush()

        # Create default accounts
        accounts = [
            Account(user_id=demo.id, name="Conta Corrente", type="corrente",
                   bank_name="Banco Digital", balance=3500.00, color="#22c55e", icon="wallet"),
            Account(user_id=demo.id, name="Cartão Principal", type="cartao_credito",
                   bank_name="Nubank", balance=-1200.00, credit_limit=5000.00,
                   closing_day=20, due_day=28, color="#8b5cf6", icon="credit-card"),
            Account(user_id=demo.id, name="Poupança", type="poupanca",
                   bank_name="Banco Digital", balance=8500.00, color="#0ea5e9", icon="piggy-bank"),
        ]
        for a in accounts:
            db.add(a)

        await db.commit()
        print("✅ Usuário demo criado: demo@copilotfinanceiro.com / Demo@123")


async def main():
    print("🚀 Iniciando seed do Copilot Financeiro...")
    await create_admin()
    await create_demo_user()
    print("✨ Seed concluído!")


if __name__ == "__main__":
    asyncio.run(main())
