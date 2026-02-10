from django import template

from apps.production.domain.order_statuses import status_ui_map

register = template.Library()

STATUS_CONFIG = status_ui_map(include_legacy=True)
_DEFAULT_STATUS = {"dot_class": "text-slate-400", "icon": "dot", "text_class": "text-slate-500"}


@register.inclusion_tag("partials/status_indicator.html")
def status_indicator(status_value, label="", muted=False):
    config = STATUS_CONFIG.get(status_value, _DEFAULT_STATUS)
    text_class = "text-slate-500" if muted else config["text_class"]
    return {
        "dot_class": config["dot_class"],
        "icon": config["icon"],
        "text_class": text_class,
        "label": label,
    }


NAV_ITEMS = [
    {"url_name": "orders_active", "label": "У роботі", "active_on": ("orders_active", "index")},
    {"url_name": "orders_completed", "label": "Завершені", "active_on": ("orders_completed",)},
    {
        "url_name": "products",
        "label": "Моделі",
        "active_on": ("products", "product_edit", "products_archive"),
    },
    {"url_name": "colors", "label": "Кольори", "active_on": ("colors", "color_edit", "colors_archive")},
    {
        "url_name": "materials",
        "label": "Матеріали",
        "active_on": ("materials", "material_edit", "materials_archive"),
    },
    {"url_name": "profile", "label": "Профіль", "active_on": ("profile", "change_password")},
]


@register.simple_tag(takes_context=True)
def get_nav_items(context):
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
