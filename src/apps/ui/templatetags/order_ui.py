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


NAV_SECTIONS = [
    {
        "key": "work",
        "label": "Виробництво",
        "emoji": "🏭",
        "items": [
            {
                "url_name": "orders_active",
                "label": "Активні",
                "active_on": ("orders_active", "index", "order_detail", "order_edit"),
            },
            {
                "url_name": "orders_completed",
                "label": "Завершені",
                "active_on": ("orders_completed",),
            },
        ],
    },
    {
        "key": "inventory",
        "label": "Склад",
        "emoji": "📦",
        "items": [
            {
                "url_name": "inventory_products",
                "label": "Готова продукція",
                "active_on": ("inventory_products",),
            },
            {
                "url_name": "inventory_wip",
                "label": "WIP",
                "active_on": ("inventory_wip",),
            },
            {
                "url_name": "inventory_materials",
                "label": "Матеріали",
                "active_on": ("inventory_materials",),
            },
        ],
    },
    {
        "key": "catalog",
        "label": "Каталог",
        "emoji": "📋",
        "items": [
            {
                "url_name": "products",
                "label": "Продукти",
                "active_on": (
                    "products",
                    "product_add",
                    "product_detail",
                    "product_edit",
                    "products_archive",
                    "color_edit",
                    "colors",
                    "colors_archive",
                    "bom_edit",
                    "product_material_edit",
                ),
            },
            {
                "url_name": "materials",
                "label": "Матеріали",
                "active_on": (
                    "materials",
                    "material_add",
                    "material_detail",
                    "material_edit",
                    "materials_archive",
                    "material_color_add",
                    "material_color_edit",
                    "material_colors_archive",
                ),
            },
        ],
    },
    {
        "key": "more",
        "label": "Ще",
        "emoji": "⋯",
        "items": [
            {
                "url_name": "customers",
                "label": "Клієнти",
                "active_on": ("customers",),
            },
            {
                "url_name": "suppliers",
                "label": "Постачальники",
                "active_on": ("suppliers",),
            },
            {
                "url_name": "purchases",
                "label": "Закупівлі",
                "active_on": ("purchases",),
            },
            {
                "url_name": "profile",
                "label": "Профіль",
                "active_on": ("profile", "change_password"),
            },
        ],
    },
]

NAV_CTA = {
    "url_name": "orders_create",
    "label": "+ Замовлення",
    "short_label": "+",
}


def _is_item_active(item: dict, current_url: str) -> bool:
    return current_url in item.get("active_on", ())


def _is_section_active(section: dict, current_url: str) -> bool:
    return any(_is_item_active(item, current_url) for item in section["items"])


@register.simple_tag(takes_context=True)
def get_nav_sections(context):
    """Return nav sections with active state computed."""
    current_url = context.get("current_url") or ""
    sections = []
    for section in NAV_SECTIONS:
        items = [
            {
                "url_name": item["url_name"],
                "label": item["label"],
                "is_active": _is_item_active(item, current_url),
            }
            for item in section["items"]
        ]
        sections.append(
            {
                "key": section["key"],
                "label": section["label"],
                "emoji": section["emoji"],
                "items": items,
                "is_active": any(item["is_active"] for item in items),
            }
        )
    return sections


@register.simple_tag(takes_context=True)
def get_nav_cta(context):
    """Return the CTA button config."""
    current_url = context.get("current_url") or ""
    return {
        "url_name": NAV_CTA["url_name"],
        "label": NAV_CTA["label"],
        "short_label": NAV_CTA["short_label"],
        "is_active": current_url == NAV_CTA["url_name"],
    }


# Legacy: keep get_nav_items for backwards compatibility during transition
NAV_ITEMS = [
    {"url_name": "orders_active", "label": "У роботі", "active_on": ("orders_active", "index")},
    {"url_name": "orders_completed", "label": "Завершені", "active_on": ("orders_completed",)},
    {
        "url_name": "products",
        "label": "Моделі",
        "active_on": ("products", "product_add", "product_edit", "products_archive"),
    },
    {
        "url_name": "materials",
        "label": "Матеріали",
        "active_on": ("materials", "material_add", "material_edit", "materials_archive"),
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


@register.filter
def get_form_field(form, field_name: str):
    """Template helper to render grouped/dynamic form fields by name."""
    return form[field_name]
