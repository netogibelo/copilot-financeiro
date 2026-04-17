from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Copilot Financeiro"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "super-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql://copilot:copilot_secret@localhost:5432/copilot_financeiro"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM: str = "noreply@copilotfinanceiro.com"

    # Admin
    ADMIN_EMAIL: str = "admin@copilotfinanceiro.com"
    ADMIN_PASSWORD: str = "Admin@123"

    # File uploads
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # Rate limiting
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_API: str = "100/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
