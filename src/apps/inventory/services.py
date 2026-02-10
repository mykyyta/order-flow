from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Variant
from apps.catalog.variants import resolve_or_create_variant
from apps.inventory.models import (
    ProductStockTransfer,
    ProductStockTransferLine,
    ProductStockMovement,
    ProductStock,
    WIPStockMovement,
    WIPStockRecord,
)
from apps.warehouses.services import resolve_warehouse_id

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.production.models import ProductionOrder
    from apps.sales.models import SalesOrderLine


class StockKey(TypedDict):
    warehouse_id: int
    variant_id: int


def get_stock_quantity(
    *,
    warehouse_id: int | None = None,
    variant_id: int | None = None,
    product_id: int | None = None,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> int:
    stock_key = _resolve_stock_key(
        warehouse_id=warehouse_id,
        variant_id=variant_id,
        product_id=product_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    lookup = _build_stock_lookup(stock_key=stock_key)

    try:
        record = ProductStock.objects.get(**lookup)
    except ProductStock.DoesNotExist:
        return 0
    return record.quantity


@transaction.atomic
def add_to_stock(
    *,
    warehouse_id: int | None = None,
    variant_id: int | None = None,
    product_id: int | None = None,
    quantity: int,
    reason: str,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
    production_order: "ProductionOrder | None" = None,
    sales_order_line: "SalesOrderLine | None" = None,
    related_transfer: ProductStockTransfer | None = None,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> ProductStock:
    stock_key = _resolve_stock_key(
        warehouse_id=warehouse_id,
        variant_id=variant_id,
        product_id=product_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    lookup = _build_stock_lookup(stock_key=stock_key)
    record, _ = ProductStock.objects.get_or_create(**lookup)
    record.quantity += quantity
    record.save(update_fields=["quantity"])

    ProductStockMovement.objects.create(
        stock_record=record,
        quantity_change=quantity,
        reason=reason,
        related_production_order=production_order,
        sales_order_line=sales_order_line,
        related_transfer=related_transfer,
        created_by=user,
        notes=notes,
    )
    return record


@transaction.atomic
def remove_from_stock(
    *,
    warehouse_id: int | None = None,
    variant_id: int | None = None,
    product_id: int | None = None,
    quantity: int,
    reason: str,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
    sales_order_line: "SalesOrderLine | None" = None,
    related_transfer: ProductStockTransfer | None = None,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> ProductStock:
    stock_key = _resolve_stock_key(
        warehouse_id=warehouse_id,
        variant_id=variant_id,
        product_id=product_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    lookup = _build_stock_lookup(stock_key=stock_key)

    try:
        record = ProductStock.objects.get(**lookup)
    except ProductStock.DoesNotExist as exc:
        raise ValueError("Недостатньо на складі: є 0") from exc

    if record.quantity < quantity:
        raise ValueError(f"Недостатньо на складі: є {record.quantity}, потрібно {quantity}")

    record.quantity -= quantity
    record.save(update_fields=["quantity"])

    ProductStockMovement.objects.create(
        stock_record=record,
        quantity_change=-quantity,
        reason=reason,
        sales_order_line=sales_order_line,
        related_transfer=related_transfer,
        created_by=user,
        notes=notes,
    )
    return record


def _resolve_stock_key(
    *,
    warehouse_id: int | None,
    variant_id: int | None,
    product_id: int | None,
    color_id: int | None,
    primary_material_color_id: int | None,
    secondary_material_color_id: int | None,
) -> StockKey:
    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    if variant_id is not None:
        variant = Variant.objects.only(
            "id",
            "product_id",
            "color_id",
            "primary_material_color_id",
            "secondary_material_color_id",
        ).get(id=variant_id)
        if product_id is not None and product_id != variant.product_id:
            raise ValueError("Provided product_id does not match variant.")
        if color_id is not None and color_id != variant.color_id:
            raise ValueError("Provided color_id does not match variant.")
        if (
            primary_material_color_id is not None
            and primary_material_color_id != variant.primary_material_color_id
        ):
            raise ValueError("Provided primary_material_color_id does not match variant.")
        if (
            secondary_material_color_id is not None
            and secondary_material_color_id != variant.secondary_material_color_id
        ):
            raise ValueError("Provided secondary_material_color_id does not match variant.")
        return {
            "warehouse_id": resolved_warehouse_id,
            "variant_id": variant.id,
        }

    if product_id is None:
        raise ValueError("Stock key requires variant_id or product_id")
    if color_id is None and primary_material_color_id is None:
        raise ValueError("Stock key requires color_id or primary_material_color_id")

    variant = resolve_or_create_variant(
        product_id=product_id,
        color_id=color_id,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
    )
    return {
        "warehouse_id": resolved_warehouse_id,
        "variant_id": variant.id,
    }


def _build_stock_lookup(*, stock_key: StockKey) -> dict[str, int | None]:
    return {
        "warehouse_id": stock_key["warehouse_id"],
        "variant_id": stock_key["variant_id"],
    }


def get_wip_stock_quantity(
    *,
    variant_id: int,
    warehouse_id: int | None = None,
) -> int:
    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    try:
        record = WIPStockRecord.objects.get(
            warehouse_id=resolved_warehouse_id,
            variant_id=variant_id,
        )
    except WIPStockRecord.DoesNotExist:
        return 0
    return record.quantity


@transaction.atomic
def add_to_wip_stock(
    *,
    variant_id: int,
    quantity: int,
    reason: str,
    warehouse_id: int | None = None,
    production_order: "ProductionOrder | None" = None,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> WIPStockRecord:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    record, _ = WIPStockRecord.objects.get_or_create(
        warehouse_id=resolved_warehouse_id,
        variant_id=variant_id,
    )
    record.quantity += quantity
    record.save(update_fields=["quantity"])

    WIPStockMovement.objects.create(
        stock_record=record,
        quantity_change=quantity,
        reason=reason,
        related_production_order=production_order,
        created_by=user,
        notes=notes,
    )
    return record


@transaction.atomic
def remove_from_wip_stock(
    *,
    variant_id: int,
    quantity: int,
    reason: str,
    warehouse_id: int | None = None,
    production_order: "ProductionOrder | None" = None,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> WIPStockRecord:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    try:
        record = WIPStockRecord.objects.get(
            warehouse_id=resolved_warehouse_id,
            variant_id=variant_id,
        )
    except WIPStockRecord.DoesNotExist as exc:
        raise ValueError("Недостатньо WIP на складі: є 0") from exc

    if record.quantity < quantity:
        raise ValueError(f"Недостатньо WIP на складі: є {record.quantity}, потрібно {quantity}")

    record.quantity -= quantity
    record.save(update_fields=["quantity"])

    WIPStockMovement.objects.create(
        stock_record=record,
        quantity_change=-quantity,
        reason=reason,
        related_production_order=production_order,
        created_by=user,
        notes=notes,
    )
    return record


@transaction.atomic
def transfer_finished_stock(
    *,
    from_warehouse_id: int,
    to_warehouse_id: int,
    variant_id: int,
    quantity: int,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> ProductStockTransfer:
    if from_warehouse_id == to_warehouse_id:
        raise ValueError("Transfer warehouses must be different")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    transfer = ProductStockTransfer.objects.create(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        status=ProductStockTransfer.Status.IN_TRANSIT,
        created_by=user,
        notes=notes,
    )
    ProductStockTransferLine.objects.create(
        transfer=transfer,
        variant_id=variant_id,
        quantity=quantity,
    )

    remove_from_stock(
        warehouse_id=from_warehouse_id,
        variant_id=variant_id,
        quantity=quantity,
        reason=ProductStockMovement.Reason.TRANSFER_OUT,
        related_transfer=transfer,
        user=user,
        notes=notes,
    )
    add_to_stock(
        warehouse_id=to_warehouse_id,
        variant_id=variant_id,
        quantity=quantity,
        reason=ProductStockMovement.Reason.TRANSFER_IN,
        related_transfer=transfer,
        user=user,
        notes=notes,
    )

    transfer.status = ProductStockTransfer.Status.COMPLETED
    transfer.completed_at = timezone.now()
    transfer.save(update_fields=["status", "completed_at"])
    return transfer
