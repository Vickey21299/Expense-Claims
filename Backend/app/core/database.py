"""
app/core/database.py
Supabase client singleton — import `supabase` wherever DB access is needed.
"""
import logging
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    """Return the shared Supabase client (lazy-initialised)."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set in .env"
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase client initialised successfully")
    return _client


# Convenience alias used throughout routers
supabase = get_supabase()
