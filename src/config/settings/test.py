"""Test settings: SQLite to avoid touching Postgres and DB name conflicts."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}
