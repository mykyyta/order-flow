"""Order service layer: create and change status."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.orders.domain.status import STATUS_FINISHED, STATUS_NEW, validate_status
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.notifications import send_order_created, send_order_finished

if TYPE_CHECKING:
    from apps.catalog.models import Color, ProductModel
    from apps.customer_orders.models import CustomerOrderLine
    from apps.materials.models import MaterialColor
    from apps.orders.models import CustomUser


@transaction.atomic
def create_order(
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
) -> Order:
    if color is None and primary_material_color is None:
        raise ValueError("Order requires color or primary material color")

    order = Order.objects.create(
        model=model,
        color=color,
        primary_material_color=primary_material_color,
        secondary_material_color=secondary_material_color,
        embroidery=embroidery,
        urgent=urgent,
        etsy=etsy,
        comment=comment,
        current_status=STATUS_NEW,
        customer_order_line=customer_order_line,
    )
    OrderStatusHistory.objects.create(
        order=order,
        new_status=STATUS_NEW,
        changed_by=created_by,
    )
    send_order_created(order=order, orders_url=orders_url)
    return order


@transaction.atomic
def change_order_status(
    *,
    orders: list[Order],
    new_status: str,
    changed_by: "CustomUser",
) -> None:
    normalized = validate_status(new_status)
    for order in orders:
        order.transition_to(normalized, changed_by)
        order.save()
        if normalized == STATUS_FINISHED:
            _handle_finished_order(order=order, changed_by=changed_by)
            send_order_finished(order=order)


def _handle_finished_order(*, order: Order, changed_by: "CustomUser") -> None:
    from apps.inventory.models import StockMovement
    from apps.inventory.services import add_to_stock

    add_to_stock(
        product_model_id=order.model_id,
        color_id=order.color_id,
        primary_material_color_id=order.primary_material_color_id,
        secondary_material_color_id=order.secondary_material_color_id,
        quantity=1,
        reason=StockMovement.Reason.PRODUCTION_IN,
        production_order=order,
        customer_order_line=order.customer_order_line,
        user=changed_by,
    )

    if order.customer_order_line_id is None:
        return

    from apps.customer_orders.services import sync_customer_order_line_production

    sync_customer_order_line_production(order.customer_order_line)
