from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException

router = APIRouter()


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "version": settings.VERSION,
        }
    except Exception as e:
        raise AppException(
            message="Service not ready",
            status_code=503,
            error_code="SERVICE_NOT_READY",
            details={"database": str(e)},
        )


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}
