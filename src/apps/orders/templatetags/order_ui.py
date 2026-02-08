from django import template
from apps.orders.domain.order_statuses import status_ui_map

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


# ---------------------------------------------------------------------------
# Navigation: single source of truth for nav links (desktop + mobile)
# ---------------------------------------------------------------------------
# To add a nav item: add one entry to NAV_ITEMS. No template duplication.
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    {"url_name": "orders_active", "label": "У роботі", "active_on": ("orders_active", "index")},
    {"url_name": "orders_completed", "label": "Завершені", "active_on": ("orders_completed",)},
    {"url_name": "product_models", "label": "Моделі", "active_on": ("product_models",)},
    {"url_name": "colors", "label": "Кольори", "active_on": ("colors",)},
    {"url_name": "materials", "label": "Матеріали", "active_on": ("materials", "material_edit")},
    {"url_name": "profile", "label": "Профіль", "active_on": ("profile", "change_password")},
]


@register.simple_tag(takes_context=True)
def get_nav_items(context):
    """Return list of nav items with is_active set from current_url. Use in base.html for nav partial."""
    current_url = context.get("current_url") or ""
    return [
        {
            "url_name": item["url_name"],
            "label": item["label"],
            "is_active": current_url in item["active_on"],
        }
        for item in NAV_ITEMS
    ]


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
