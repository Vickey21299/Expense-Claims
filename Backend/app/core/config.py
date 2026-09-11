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
    LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "json")  # 'json' or 'text'


settings = Settings()
