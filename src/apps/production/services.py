from __future__ import annotations

from typing import TYPE_CHECKING

from apps.orders.services import change_order_status, create_order

if TYPE_CHECKING:
    from apps.catalog.models import Color, ProductModel
    from apps.customer_orders.models import CustomerOrderLine
    from apps.materials.models import MaterialColor
    from apps.orders.models import CustomUser, Order


def create_production_order(
    *,
    model: "ProductModel",
    color: "Color | None",
    primary_material_color: "MaterialColor | None" = None,
    secondary_material_color: "MaterialColor | None" = None,
    embroidery: bool,
    urgent: bool,
    etsy: bool,
    comment: str | None,
    created_by: "CustomUser",
    orders_url: str | None,
    customer_order_line: "CustomerOrderLine | None" = None,
) -> "Order":
    return create_order(
        model=model,
        color=color,
        primary_material_color=primary_material_color,
        secondary_material_color=secondary_material_color,
        embroidery=embroidery,
        urgent=urgent,
        etsy=etsy,
        comment=comment,
        created_by=created_by,
        orders_url=orders_url,
        customer_order_line=customer_order_line,
    )


def change_production_order_status(
    *,
    production_orders: list["Order"],
    new_status: str,
    changed_by: "CustomUser",
) -> None:
    change_order_status(
        orders=production_orders,
        new_status=new_status,
        changed_by=changed_by,
    )
