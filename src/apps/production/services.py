"""Production order service layer: create and change status."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.db import transaction

from apps.catalog.variants import resolve_or_create_variant
from apps.inventory.domain import Quantity, VariantId, WarehouseId
from apps.warehouses.services import get_default_warehouse
from apps.production.notifications import send_order_created, send_order_finished
from apps.production.domain.status import STATUS_DONE, STATUS_NEW, validate_status
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.catalog.models import Color, Product, Variant
    from apps.materials.models import MaterialColor
    from apps.sales.models import SalesOrderLine


@transaction.atomic
def create_production_order(
    *,
    product: "Product",
    variant: "Variant | None" = None,
    color: "Color | None" = None,
    primary_material_color: "MaterialColor | None" = None,
    secondary_material_color: "MaterialColor | None" = None,
    is_embroidery: bool,
    is_urgent: bool,
    is_etsy: bool,
    comment: str | None,
    created_by: "AbstractBaseUser",
    orders_url: str | None,
    sales_order_line: "SalesOrderLine | None" = None,
) -> ProductionOrder:
    if variant is None:
        if color is None and primary_material_color is None:
            raise ValueError("Order requires color or primary material color")
        variant = resolve_or_create_variant(
            product_id=product.id,
            color_id=color.id if color else None,
            primary_material_color_id=primary_material_color.id if primary_material_color else None,
            secondary_material_color_id=secondary_material_color.id if secondary_material_color else None,
        )
    if variant is None:
        raise ValueError("Order requires resolvable variant")

    order = ProductionOrder.objects.create(
        product=product,
        variant=variant,
        is_embroidery=is_embroidery,
        is_urgent=is_urgent,
        is_etsy=is_etsy,
        comment=comment,
        status=STATUS_NEW,
        sales_order_line=sales_order_line,
    )
    ProductionOrderStatusHistory.objects.create(
        order=order,
        new_status=STATUS_NEW,
        changed_by=created_by,
    )

    send_order_created(order=order, orders_url=orders_url)
    return order


@transaction.atomic
def change_production_order_status(
    *,
    production_orders: list[ProductionOrder],
    new_status: str,
    changed_by: "AbstractBaseUser",
    on_order_done: Callable[[ProductionOrder, "AbstractBaseUser"], None] | None = None,
    on_sales_line_done: Callable[["SalesOrderLine"], None] | None = None,
) -> None:
    normalized = validate_status(new_status)
    order_done_handler = on_order_done or _add_finished_stock
    for order in production_orders:
        order.transition_to(normalized, changed_by)
        order.save()
        if normalized == STATUS_DONE:
            order_done_handler(order, changed_by)
            if order.sales_order_line_id and on_sales_line_done is not None:
                on_sales_line_done(order.sales_order_line)

            send_order_finished(order=order)


def _add_finished_stock(
    order: ProductionOrder,
    changed_by: "AbstractBaseUser",
) -> None:
    from apps.inventory.models import ProductStockMovement
    from apps.inventory.services import add_to_stock

    warehouse_id = WarehouseId(get_default_warehouse().id)
    add_to_stock(
        warehouse_id=warehouse_id,
        variant_id=VariantId(order.variant_id),
        product_id=order.product_id,
        quantity=Quantity(1),
        reason=ProductStockMovement.Reason.PRODUCTION_IN,
        production_order=order,
        sales_order_line=order.sales_order_line,
        user=changed_by,
    )
