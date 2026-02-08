"""Order service layer: create and change status."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.orders.domain.status import STATUS_FINISHED, STATUS_NEW, validate_status
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.notifications import send_order_created, send_order_finished

if TYPE_CHECKING:
    from apps.catalog.models import Color, ProductModel
    from apps.orders.models import CustomUser


@transaction.atomic
def create_order(
    *,
    model: "ProductModel",
    color: "Color",
    embroidery: bool,
    urgent: bool,
    etsy: bool,
    comment: str | None,
    created_by: "CustomUser",
    orders_url: str | None,
) -> Order:
    order = Order.objects.create(
        model=model,
        color=color,
        embroidery=embroidery,
        urgent=urgent,
        etsy=etsy,
        comment=comment,
        current_status=STATUS_NEW,
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
            send_order_finished(order=order)
