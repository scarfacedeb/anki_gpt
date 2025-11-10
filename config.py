import os
from typing import Optional

def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get a boolean value from environment variables.
    Accepts: true, yes, 1 (case-insensitive) as True.
    """
    value = os.getenv(key, "").lower()
    if value in ("true", "yes", "1"):
        return True
    if value in ("false", "no", "0"):
        return False
    return default

# Anki configuration
ENABLE_ANKI_SYNC = get_env_bool("ENABLE_ANKI_SYNC", default=True)
ANKI_CONNECT_URL = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "words.db")
