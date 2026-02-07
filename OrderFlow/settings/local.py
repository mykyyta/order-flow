from .base import ALLOWED_HOSTS, SECRET_KEY, env_bool
from .base import *  # noqa: F401,F403

DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = SECRET_KEY or "local-dev-insecure-secret-key"

ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
