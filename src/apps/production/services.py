from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.catalog.models import Color, ProductModel
    from apps.materials.models import MaterialColor
    from apps.production.models import ProductionOrder
    from apps.sales.models import SalesOrderLine


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
    created_by: "AbstractBaseUser",
    orders_url: str | None,
    customer_order_line: "SalesOrderLine | None" = None,
) -> "ProductionOrder":
    from apps.orders.services import create_order

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
        via_v2_context=True,
    )


def change_production_order_status(
    *,
    production_orders: list["ProductionOrder"],
    new_status: str,
    changed_by: "AbstractBaseUser",
) -> None:
    from apps.orders.services import change_order_status

    change_order_status(
        orders=production_orders,
        new_status=new_status,
        changed_by=changed_by,
        via_v2_context=True,
    )
