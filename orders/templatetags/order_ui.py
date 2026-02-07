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
