import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Numeric, Integer, Date, ForeignKey, Text, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan", foreign_keys="[Account.user_id]")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan", foreign_keys="[Transaction.user_id]")
    categories: Mapped[List["Category"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    credit_limit: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    closing_day: Mapped[Optional[int]] = mapped_column(Integer)
    due_day: Mapped[Optional[int]] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    icon: Mapped[str] = mapped_column(String(50), default="wallet")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    include_in_total: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="accounts", foreign_keys=[user_id])
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account", foreign_keys="[Transaction.account_id]")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="tag")
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("categories.id"))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("accounts.id", ondelete="CASCADE"))
    category_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("categories.id"))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    original_description: Mapped[Optional[str]] = mapped_column(String(500))
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(255)))
    installment_total: Mapped[Optional[int]] = mapped_column(Integer)
    installment_current: Mapped[Optional[int]] = mapped_column(Integer)
    installment_group_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    transfer_account_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("accounts.id"))
    import_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_group_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="transactions", foreign_keys=[user_id])
    account: Mapped["Account"] = relationship(back_populates="transactions", foreign_keys=[account_id])
    transfer_account: Mapped[Optional["Account"]] = relationship(foreign_keys=[transfer_account_id])
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")


class CategoryLearning(Base):
    __tablename__ = "category_learning"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("categories.id"))
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=1)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SubscriptionDetected(Base):
    __tablename__ = "subscriptions_detected"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("categories.id"))
    account_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("accounts.id"))
    frequency_days: Mapped[int] = mapped_column(Integer, default=30)
    last_detected_at: Mapped[Optional[datetime]] = mapped_column(Date)
    next_expected_at: Mapped[Optional[datetime]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="suspected")
    pattern_keyword: Mapped[Optional[str]] = mapped_column(String(255))
    transaction_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InstallmentDetected(Base):
    __tablename__ = "installments_detected"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    installment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    total_installments: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_installments: Mapped[int] = mapped_column(Integer, default=0)
    remaining_installments: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(Date)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date)
    category_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("categories.id"))
    account_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("accounts.id"))
    group_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    messages: Mapped[dict] = mapped_column(JSONB, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    admin_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    account_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("accounts.id"))
    filename: Mapped[Optional[str]] = mapped_column(String(500))
    file_type: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    imported_transactions: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_transactions: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CashflowPrediction(Base):
    __tablename__ = "cashflow_predictions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    prediction_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    predicted_balance: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    predicted_income: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    predicted_expense: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
