from django import template
from orders.domain.order_statuses import status_ui_map

register = template.Library()

# ---------------------------------------------------------------------------
# Status indicator: dot/icon + text (no background fill)
# ---------------------------------------------------------------------------
# Each status maps to:
#   dot_class  – Tailwind class for the indicator color (text-* used for dots and SVG icons)
#   icon       – "dot", "play", "pause", "none"
#   text_class – Tailwind class for the label text color
#
# To add a new status, add one entry here. Zero template changes required.
# ---------------------------------------------------------------------------

STATUS_CONFIG = status_ui_map(include_legacy=True)

_DEFAULT_STATUS = {"dot_class": "text-slate-400", "icon": "dot", "text_class": "text-slate-500"}


@register.inclusion_tag("partials/status_indicator.html")
def status_indicator(status_value, label="", muted=False):
    """Render a status indicator: label text + colored dot (or icon). muted=True for list context (lighter text)."""
    config = STATUS_CONFIG.get(status_value, _DEFAULT_STATUS)
    text_class = "text-slate-500" if muted else config["text_class"]
    return {
        "dot_class": config["dot_class"],
        "icon": config["icon"],
        "text_class": text_class,
        "label": label,
    }


# ---------------------------------------------------------------------------
# Message alerts (Django messages framework)
# ---------------------------------------------------------------------------


@register.filter
def message_alert_class(message_tags: str) -> str:
    """Return CSS class names for message alert (alert + alert-{type})."""
    tag_to_class = {
        "debug": "alert alert-debug",
        "info": "alert alert-info",
        "success": "alert alert-success",
        "warning": "alert alert-warning",
        "error": "alert alert-error",
    }
    for tag in (message_tags or "").split():
        if tag in tag_to_class:
            return tag_to_class[tag]
    return "alert alert-info"
