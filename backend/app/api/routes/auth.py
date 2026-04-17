from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr
import httpx

from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, decode_token, generate_random_token
)
from app.core.config import settings
from app.models import User
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# =====================================================
# SCHEMAS
# =====================================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# =====================================================
# REGISTER
# =====================================================

@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing email
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 8 caracteres")

    verification_token = generate_random_token()
    user = User(
        name=data.name,
        email=data.email,
        password_hash=get_password_hash(data.password),
        email_verification_token=verification_token,
        is_email_verified=False,
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    }


# =====================================================
# LOGIN
# =====================================================

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="Conta temporariamente bloqueada. Tente novamente mais tarde.")

    if not user.password_hash or not verify_password(data.password, user.password_hash):
        # Increment failed attempts
        attempts = (user.failed_login_attempts or 0) + 1
        locked_until = None
        if attempts >= 5:
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            attempts = 0
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_attempts=attempts, locked_until=locked_until)
        )
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada")

    # Reset failed attempts on success
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(failed_login_attempts=0, locked_until=None, last_login_at=datetime.now(timezone.utc))
    )

    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    }


# =====================================================
# GOOGLE LOGIN
# =====================================================

@router.post("/google", response_model=TokenResponse)
async def google_login(data: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    # Verify Google token
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={data.token}"
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Token Google inválido")
        google_data = response.json()

    if google_data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token Google inválido para este app")

    google_id = google_data.get("sub")
    email = google_data.get("email")
    name = google_data.get("name", email)
    avatar_url = google_data.get("picture")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Conta desativada")
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(google_id=google_id, avatar_url=avatar_url, last_login_at=datetime.now(timezone.utc))
        )
    else:
        user = User(
            name=name,
            email=email,
            google_id=google_id,
            avatar_url=avatar_url,
            is_email_verified=True,
        )
        db.add(user)
        await db.flush()

    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    }


# =====================================================
# REFRESH TOKEN
# =====================================================

@router.post("/refresh", response_model=dict)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")

    access_token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================
# FORGOT PASSWORD
# =====================================================

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user:
        reset_token = generate_random_token()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(password_reset_token=reset_token, password_reset_expires=expires)
        )
        # TODO: send email with reset link

    return {"message": "Se o e-mail existir, você receberá as instruções em breve."}


# =====================================================
# RESET PASSWORD
# =====================================================

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            User.password_reset_token == data.token,
            User.password_reset_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 8 caracteres")

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            password_hash=get_password_hash(data.new_password),
            password_reset_token=None,
            password_reset_expires=None,
        )
    )
    return {"message": "Senha redefinida com sucesso"}
