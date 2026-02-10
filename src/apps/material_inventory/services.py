from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.material_inventory.models import (
    MaterialStockMovement,
    MaterialStockRecord,
    MaterialStockTransfer,
    MaterialStockTransferLine,
)
from apps.materials.models import Material, MaterialColor
from apps.warehouses.services import resolve_warehouse_id

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from apps.procurement.models import GoodsReceiptLine, PurchaseOrderLine


@transaction.atomic
def add_material_stock(
    *,
    warehouse_id: int | None = None,
    material: Material,
    quantity: Decimal,
    unit: str,
    reason: str,
    material_color: MaterialColor | None = None,
    related_purchase_order_line: PurchaseOrderLine | None = None,
    related_receipt_line: GoodsReceiptLine | None = None,
    created_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> MaterialStockRecord:
    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    stock_record, _ = MaterialStockRecord.objects.get_or_create(
        warehouse_id=resolved_warehouse_id,
        material=material,
        material_color=material_color,
        unit=unit,
    )
    stock_record.quantity += quantity_decimal
    stock_record.save(update_fields=["quantity", "updated_at"])

    MaterialStockMovement.objects.create(
        stock_record=stock_record,
        quantity_change=quantity_decimal,
        reason=reason,
        related_purchase_order_line=related_purchase_order_line,
        related_receipt_line=related_receipt_line,
        created_by=created_by,
        notes=notes,
    )
    return stock_record


@transaction.atomic
def remove_material_stock(
    *,
    warehouse_id: int | None = None,
    material: Material,
    quantity: Decimal,
    unit: str,
    reason: str,
    material_color: MaterialColor | None = None,
    related_purchase_order_line: PurchaseOrderLine | None = None,
    created_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> MaterialStockRecord:
    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    try:
        stock_record = MaterialStockRecord.objects.get(
            warehouse_id=resolved_warehouse_id,
            material=material,
            material_color=material_color,
            unit=unit,
        )
    except MaterialStockRecord.DoesNotExist as exc:
        raise ValueError("Недостатньо на складі: є 0") from exc

    if stock_record.quantity < quantity_decimal:
        raise ValueError(f"Недостатньо на складі: є {stock_record.quantity}, потрібно {quantity_decimal}")

    stock_record.quantity -= quantity_decimal
    stock_record.save(update_fields=["quantity", "updated_at"])

    MaterialStockMovement.objects.create(
        stock_record=stock_record,
        quantity_change=-quantity_decimal,
        reason=reason,
        related_purchase_order_line=related_purchase_order_line,
        created_by=created_by,
        notes=notes,
    )
    return stock_record


@transaction.atomic
def transfer_material_stock(
    *,
    from_warehouse_id: int,
    to_warehouse_id: int,
    material: Material,
    quantity: Decimal,
    unit: str,
    material_color: MaterialColor | None = None,
    created_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> MaterialStockTransfer:
    if from_warehouse_id == to_warehouse_id:
        raise ValueError("Transfer warehouses must be different")

    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    transfer = MaterialStockTransfer.objects.create(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        status=MaterialStockTransfer.Status.IN_TRANSIT,
        created_by=created_by,
        notes=notes,
    )
    MaterialStockTransferLine.objects.create(
        transfer=transfer,
        material=material,
        material_color=material_color,
        quantity=quantity_decimal,
        unit=unit,
    )

    remove_material_stock(
        warehouse_id=from_warehouse_id,
        material=material,
        material_color=material_color,
        quantity=quantity_decimal,
        unit=unit,
        reason=MaterialStockMovement.Reason.TRANSFER_OUT,
        created_by=created_by,
        notes=notes,
    )
    add_material_stock(
        warehouse_id=to_warehouse_id,
        material=material,
        material_color=material_color,
        quantity=quantity_decimal,
        unit=unit,
        reason=MaterialStockMovement.Reason.TRANSFER_IN,
        created_by=created_by,
        notes=notes,
    )

    transfer.status = MaterialStockTransfer.Status.COMPLETED
    transfer.completed_at = timezone.now()
    transfer.save(update_fields=["status", "completed_at"])
    return transfer
