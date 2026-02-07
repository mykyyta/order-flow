from django import template

register = template.Library()


@register.filter
def status_badge_class(status_value: str) -> str:
    status_to_class = {
        "new": "bg-success",
        "embroidery": "bg-warning text-dark",
        "almost_finished": "bg-primary",
        "finished": "bg-info text-dark",
        "on_hold": "bg-secondary",
    }
    return status_to_class.get(status_value, "bg-light text-dark")


@register.filter
def message_alert_class(message_tags: str) -> str:
    tag_to_class = {
        "debug": "secondary",
        "info": "info",
        "success": "success",
        "warning": "warning",
        "error": "danger",
    }
    for tag in (message_tags or "").split():
        if tag in tag_to_class:
            return tag_to_class[tag]
    return "info"
