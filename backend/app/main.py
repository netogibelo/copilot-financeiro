from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import (
    auth, users, accounts, categories, transactions,
    imports, subscriptions, installments, cashflow,
    ai_consultant, admin, analytics, reports
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Copilot Financeiro starting up...")
    os.makedirs("uploads", exist_ok=True)
    yield
    logger.info("👋 Copilot Financeiro shutting down...")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Copilot Financeiro API",
    description="Plataforma de gestão financeira pessoal inteligente",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routers
prefix = "/api/v1"
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{prefix}/users", tags=["Users"])
app.include_router(accounts.router, prefix=f"{prefix}/accounts", tags=["Accounts"])
app.include_router(categories.router, prefix=f"{prefix}/categories", tags=["Categories"])
app.include_router(transactions.router, prefix=f"{prefix}/transactions", tags=["Transactions"])
app.include_router(imports.router, prefix=f"{prefix}/imports", tags=["Imports"])
app.include_router(subscriptions.router, prefix=f"{prefix}/subscriptions", tags=["Subscriptions"])
app.include_router(installments.router, prefix=f"{prefix}/installments", tags=["Installments"])
app.include_router(cashflow.router, prefix=f"{prefix}/cashflow", tags=["Cashflow"])
app.include_router(ai_consultant.router, prefix=f"{prefix}/ai", tags=["AI Consultant"])
app.include_router(admin.router, prefix=f"{prefix}/admin", tags=["Admin"])
app.include_router(analytics.router, prefix=f"{prefix}/analytics", tags=["Analytics"])
app.include_router(reports.router, prefix=f"{prefix}/reports", tags=["Reports"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
