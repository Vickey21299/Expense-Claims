"""
app/routers/health.py
Liveness and database connectivity checks.
"""
import logging
from fastapi import APIRouter, HTTPException
from app.core.database import supabase

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    summary="Liveness check",
    description="Returns 200 if the API process is alive.",
)
def health_check():
    return {"status": "ok", "service": "expense-claims-api"}


@router.get(
    "/db",
    summary="Database connectivity check",
    description="Pings Supabase — returns number of claims in DB to confirm live connection.",
)
def db_health_check():
    try:
        response = supabase.table("claims").select("id", count="exact").limit(1).execute()
        count = response.count if response.count is not None else len(response.data)
        logger.info(f"DB health check passed (claims count: {count})")
        return {
            "status": "ok",
            "database": "connected",
            "claims_in_db": count,
        }
    except Exception as exc:
        logger.error("DB health check failed", exc_info=exc)
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}")
