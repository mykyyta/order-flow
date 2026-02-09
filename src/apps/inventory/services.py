from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.inventory.models import StockMovement, StockRecord

if TYPE_CHECKING:
    from apps.customer_orders.models import CustomerOrderLine
    from apps.orders.models import CustomUser, Order


def get_stock_quantity(
    *,
    product_model_id: int,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> int:
    lookup = _build_stock_lookup(
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )

    try:
        record = StockRecord.objects.get(**lookup)
    except StockRecord.DoesNotExist:
        return 0
    return record.quantity


@transaction.atomic
def add_to_stock(
    *,
    product_model_id: int,
    quantity: int,
    reason: str,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
    production_order: "Order | None" = None,
    customer_order_line: "CustomerOrderLine | None" = None,
    user: "CustomUser | None" = None,
    notes: str = "",
) -> StockRecord:
    lookup = _build_stock_lookup(
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    record, _ = StockRecord.objects.get_or_create(**lookup)
    record.quantity += quantity
    record.save(update_fields=["quantity"])

    StockMovement.objects.create(
        stock_record=record,
        quantity_change=quantity,
        reason=reason,
        related_production_order=production_order,
        related_customer_order_line=customer_order_line,
        created_by=user,
        notes=notes,
    )
    return record


@transaction.atomic
def remove_from_stock(
    *,
    product_model_id: int,
    quantity: int,
    reason: str,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
    customer_order_line: "CustomerOrderLine | None" = None,
    user: "CustomUser | None" = None,
    notes: str = "",
) -> StockRecord:
    lookup = _build_stock_lookup(
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )

    try:
        record = StockRecord.objects.get(**lookup)
    except StockRecord.DoesNotExist as exc:
        raise ValueError("Недостатньо на складі: є 0") from exc

    if record.quantity < quantity:
        raise ValueError(f"Недостатньо на складі: є {record.quantity}, потрібно {quantity}")

    record.quantity -= quantity
    record.save(update_fields=["quantity"])

    StockMovement.objects.create(
        stock_record=record,
        quantity_change=-quantity,
        reason=reason,
        related_customer_order_line=customer_order_line,
        created_by=user,
        notes=notes,
    )
    return record


def _build_stock_lookup(
    *,
    product_model_id: int,
    color_id: int | None,
    primary_material_color_id: int | None,
    secondary_material_color_id: int | None,
) -> dict[str, int | None]:
    if color_id is None and primary_material_color_id is None:
        raise ValueError("Stock key requires color_id or primary_material_color_id")

    return {
        "product_model_id": product_model_id,
        "color_id": color_id,
        "primary_material_color_id": primary_material_color_id,
        "secondary_material_color_id": secondary_material_color_id,
    }
