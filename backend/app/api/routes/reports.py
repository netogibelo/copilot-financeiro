from fastapi import APIRouter, Depends, Query
from datetime import date
from app.core.security import get_current_user
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.analytics import reports_router

router = reports_router
