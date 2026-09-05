"""Configuration package."""
from .settings import (
    BASE_DIR,
    SEEN_JOBS_FILE,
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    NOTIFY_EMAIL,
    STRICT_ROLE_MATCH,
    DEFAULT_HEADERS,
)
from .keywords import INTERN_KEYWORDS, ROLE_KEYWORDS

__all__ = [
    "BASE_DIR",
    "SEEN_JOBS_FILE",
    "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
    "NOTIFY_EMAIL",
    "STRICT_ROLE_MATCH",
    "DEFAULT_HEADERS",
    "INTERN_KEYWORDS",
    "ROLE_KEYWORDS",
]
