"""
main.py — Expense Claims API
FastAPI entry point: registers all routers, middleware, and lifecycle hooks.

Run:  uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health, users, claims, reviews, payments, documents, verification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Expense Claims API starting",
        extra={"version": settings.APP_VERSION, "supabase_url": settings.SUPABASE_URL},
    )
    yield
    logger.info("Expense Claims API shutting down")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(health.router,   prefix=API_PREFIX)
app.include_router(users.router,    prefix=API_PREFIX)
app.include_router(claims.router,   prefix=API_PREFIX)
app.include_router(reviews.router,  prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(verification.router, prefix=API_PREFIX)

# Root redirect → docs
@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "Expense Claims API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "db_health": "/api/v1/health/db",
    }
