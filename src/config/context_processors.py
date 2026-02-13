"""Context processors for templates. Brand/site name is centralized here and in settings."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest

from apps.ui.themes import DEFAULT_THEME, normalize_theme


def site_brand(request: HttpRequest) -> dict[str, str]:
    """Expose site name and wordmark to all templates. Single source of truth: settings."""
    return {
        "site_name": getattr(settings, "SITE_NAME", "Pult") or "Pult",
        "site_wordmark": getattr(settings, "SITE_WORDMARK", "PULT") or "PULT",
        "site_emoji": getattr(settings, "SITE_EMOJI", "🎛️") or "🎛️",
    }


def theme(request: HttpRequest) -> dict[str, str | None]:
    """Expose the active UI theme to all templates.

    Priority:
    1) `?theme=...` (preview; `theme=default` clears)
    2) authenticated user's saved theme
    3) DEFAULT_THEME
    """
    raw = request.GET.get("theme")
    if raw is not None:
        if raw.strip() in {"default", "none"}:
            return {"active_theme": None}
        preview = normalize_theme(raw)
        if preview is not None:
            return {"active_theme": preview}

    if getattr(request.user, "is_authenticated", False):
        user_theme = normalize_theme(getattr(request.user, "theme", None))
        if user_theme is not None:
            return {"active_theme": user_theme}

    return {"active_theme": DEFAULT_THEME}
