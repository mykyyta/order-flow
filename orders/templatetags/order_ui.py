from django import template

register = template.Library()


@register.filter
def status_badge_class(status_value: str) -> str:
    base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
    status_to_class = {
        "new": "bg-emerald-100 text-emerald-700",
        "embroidery": "bg-amber-100 text-amber-800",
        "almost_finished": "bg-blue-100 text-blue-700",
        "finished": "bg-slate-100 text-slate-600",
        "on_hold": "bg-red-100 text-red-700",
    }
    colors = status_to_class.get(status_value, "bg-slate-100 text-slate-600")
    return f"{base} {colors}"


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
