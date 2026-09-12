"""
app/core/config.py
Central settings — loaded once from .env via pydantic-settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Supabase
    SUPABASE_URL: str = os.environ.get("VITE_SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("VITE_SUPABASE_ANON_KEY", "")

    # Gemini
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Storage
    STORAGE_BUCKET: str = os.environ.get("STORAGE_BUCKET", "expense-receipts")
    OCR_MAX_FILE_SIZE_MB: int = int(os.environ.get("OCR_MAX_FILE_SIZE_MB", "10"))

    # App
    APP_TITLE: str = "Expense Claims API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "FastAPI backend for the Expense Claim system. "
        "Manages claims, reviews, verification, and payments."
    )

    # CORS — comma-separated origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    # Logging
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


settings = Settings()
