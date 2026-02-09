from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.catalog.variants import resolve_or_create_product_variant
from apps.inventory.models import StockMovement, StockRecord

if TYPE_CHECKING:
    from apps.customer_orders.models import CustomerOrderLine
    from apps.orders.models import CustomUser, Order


class StockKey(TypedDict):
    product_variant_id: int | None
    product_model_id: int
    color_id: int | None
    primary_material_color_id: int | None
    secondary_material_color_id: int | None


def get_stock_quantity(
    *,
    product_variant_id: int | None = None,
    product_model_id: int | None = None,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> int:
    stock_key = _resolve_stock_key(
        product_variant_id=product_variant_id,
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    lookup = _build_stock_lookup(stock_key=stock_key)

    try:
        record = StockRecord.objects.get(**lookup)
    except StockRecord.DoesNotExist:
        return 0
    return record.quantity


@transaction.atomic
def add_to_stock(
    *,
    product_variant_id: int | None = None,
    product_model_id: int | None = None,
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
    stock_key = _resolve_stock_key(
        product_variant_id=product_variant_id,
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    if stock_key["product_variant_id"] is not None:
        product_variant = ProductVariant.objects.get(id=stock_key["product_variant_id"])
    else:
        product_variant = resolve_or_create_product_variant(
            product_model_id=stock_key["product_model_id"],
            color_id=stock_key["color_id"],
            primary_material_color_id=stock_key["primary_material_color_id"],
            secondary_material_color_id=stock_key["secondary_material_color_id"],
        )
    lookup = _build_stock_lookup(stock_key=stock_key)
    record, _ = StockRecord.objects.get_or_create(**lookup)
    if product_variant is not None and record.product_variant_id is None:
        record.product_variant = product_variant
    record.quantity += quantity
    update_fields = ["quantity"]
    if product_variant is not None and record.product_variant_id == product_variant.id:
        update_fields.append("product_variant")
    record.save(update_fields=update_fields)

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
    product_variant_id: int | None = None,
    product_model_id: int | None = None,
    quantity: int,
    reason: str,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
    customer_order_line: "CustomerOrderLine | None" = None,
    user: "CustomUser | None" = None,
    notes: str = "",
) -> StockRecord:
    stock_key = _resolve_stock_key(
        product_variant_id=product_variant_id,
        product_model_id=product_model_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    lookup = _build_stock_lookup(stock_key=stock_key)

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


def _resolve_stock_key(
    *,
    product_variant_id: int | None,
    product_model_id: int | None,
    color_id: int | None,
    primary_material_color_id: int | None,
    secondary_material_color_id: int | None,
) -> StockKey:
    if product_variant_id is not None:
        variant = ProductVariant.objects.only(
            "id",
            "product_id",
            "color_id",
            "primary_material_color_id",
            "secondary_material_color_id",
        ).get(id=product_variant_id)
        if product_model_id is not None and product_model_id != variant.product_id:
            raise ValueError("Provided product_model_id does not match product_variant.")
        return {
            "product_variant_id": variant.id,
            "product_model_id": variant.product_id,
            "color_id": variant.color_id,
            "primary_material_color_id": variant.primary_material_color_id,
            "secondary_material_color_id": variant.secondary_material_color_id,
        }

    if product_model_id is None:
        raise ValueError("Stock key requires product_variant_id or product_model_id")
    if color_id is None and primary_material_color_id is None:
        raise ValueError("Stock key requires color_id or primary_material_color_id")

    return {
        "product_variant_id": None,
        "product_model_id": product_model_id,
        "color_id": color_id,
        "primary_material_color_id": primary_material_color_id,
        "secondary_material_color_id": secondary_material_color_id,
    }


def _build_stock_lookup(*, stock_key: StockKey) -> dict[str, int | None]:
    return {
        "product_model_id": stock_key["product_model_id"],
        "color_id": stock_key["color_id"],
        "primary_material_color_id": stock_key["primary_material_color_id"],
        "secondary_material_color_id": stock_key["secondary_material_color_id"],
    }
