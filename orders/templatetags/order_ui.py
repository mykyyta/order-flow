from django import template

register = template.Library()

# ---------------------------------------------------------------------------
# Status indicator: dot/icon + text (no background fill)
# ---------------------------------------------------------------------------
# Each status maps to:
#   dot_class  – Tailwind class for the indicator color (bg-* for dots, text-* for SVG icons)
#   icon       – "dot" (default), "pause" (on_hold), "check" (finished)
#   text_class – Tailwind class for the label text color
#
# To add a new status, add one entry here. Zero template changes required.
# ---------------------------------------------------------------------------

STATUS_CONFIG = {
    "new":             {"dot_class": "bg-emerald-500", "icon": "dot",   "text_class": "text-slate-700"},
    "embroidery":      {"dot_class": "bg-orange-500",  "icon": "dot",   "text_class": "text-slate-700"},
    "almost_finished": {"dot_class": "bg-sky-500",     "icon": "dot",   "text_class": "text-slate-700"},
    "on_hold":         {"dot_class": "text-rose-500",  "icon": "pause", "text_class": "text-slate-700"},
    "finished":        {"dot_class": "text-slate-400", "icon": "check", "text_class": "text-slate-500"},
}

_DEFAULT_STATUS = {"dot_class": "bg-slate-400", "icon": "dot", "text_class": "text-slate-500"}


@register.inclusion_tag("partials/status_indicator.html")
def status_indicator(status_value, label=""):
    """Render a status indicator: colored dot (or icon) + label text."""
    config = STATUS_CONFIG.get(status_value, _DEFAULT_STATUS)
    return {
        "dot_class": config["dot_class"],
        "icon": config["icon"],
        "text_class": config["text_class"],
        "label": label,
    }


# ---------------------------------------------------------------------------
# Message alerts (Django messages framework)
# ---------------------------------------------------------------------------

@register.filter
def message_alert_class(message_tags: str) -> str:
    tag_to_class = {
        "debug": "rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700",
        "info": "rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700",
        "success": "rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700",
        "warning": "rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800",
        "error": "rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700",
    }
    for tag in (message_tags or "").split():
        if tag in tag_to_class:
            return tag_to_class[tag]
    return tag_to_class["info"]
