"""Context processors for templates. Brand/site name is centralized here and in settings."""

from django.conf import settings


def site_brand(request):
    """Expose site name and wordmark to all templates. Single source of truth: settings."""
    return {
        "site_name": getattr(settings, "SITE_NAME", "Pult"),
        "site_wordmark": getattr(settings, "SITE_WORDMARK", "PULT"),
        "site_emoji": getattr(settings, "SITE_EMOJI", "🎛️"),
    }
