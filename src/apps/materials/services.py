from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import BundleComponent, ProductMaterial
from apps.materials.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    Material,
    MaterialColor,
    MaterialStockMovement,
    MaterialStock,
    MaterialStockTransfer,
    MaterialStockTransferLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from apps.sales.models import SalesOrderLine

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


@dataclass(frozen=True)
class MaterialRequirement:
    material_id: int
    material_name: str
    unit: str
    quantity: Decimal


def calculate_material_requirements_for_sales_order_line(
    *,
    line: SalesOrderLine,
) -> list[MaterialRequirement]:
    totals: dict[tuple[int, str], Decimal] = {}
    labels: dict[int, str] = {}

    for product_id, produced_quantity in _iter_line_product_quantities(line=line):
        for norm in ProductMaterial.objects.filter(
            product_id=product_id,
            quantity_per_unit__isnull=False,
        ).select_related("material"):
            # unit is required when quantity_per_unit is set (model constraint)
            key = (norm.material_id, norm.unit)
            quantity = norm.quantity_per_unit * produced_quantity
            totals[key] = totals.get(key, Decimal("0")) + quantity
            labels[norm.material_id] = norm.material.name

    requirements = [
        MaterialRequirement(
            material_id=material_id,
            material_name=labels[material_id],
            unit=unit,
            quantity=quantity.quantize(Decimal("0.01")),
        )
        for (material_id, unit), quantity in totals.items()
    ]
    return sorted(requirements, key=lambda item: item.material_name)


def _iter_line_product_quantities(*, line: SalesOrderLine) -> list[tuple[int, Decimal]]:
    if not line.is_bundle:
        return [(line.product_id, Decimal(line.quantity))]

    bundle_components = BundleComponent.objects.filter(bundle_id=line.product_id)
    return [
        (component.component_id, Decimal(line.quantity * component.quantity))
        for component in bundle_components
    ]


@transaction.atomic
def add_material_stock(
    *,
    material: Material,
    quantity: Decimal,
    unit: str,
    reason: str,
    warehouse_id: int,
    material_color: MaterialColor | None = None,
    related_purchase_order_line: PurchaseOrderLine | None = None,
    related_receipt_line: GoodsReceiptLine | None = None,
    related_transfer: MaterialStockTransfer | None = None,
    created_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> MaterialStock:
    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    stock_record, _ = MaterialStock.objects.get_or_create(
        warehouse_id=warehouse_id,
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
        related_transfer=related_transfer,
        created_by=created_by,
        notes=notes,
    )
    return stock_record


@transaction.atomic
def remove_material_stock(
    *,
    material: Material,
    quantity: Decimal,
    unit: str,
    reason: str,
    warehouse_id: int,
    material_color: MaterialColor | None = None,
    related_purchase_order_line: PurchaseOrderLine | None = None,
    related_transfer: MaterialStockTransfer | None = None,
    created_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> MaterialStock:
    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    stock_record = (
        MaterialStock.objects.for_warehouse(warehouse_id)
        .for_material(material.id)
        .filter(material_color=material_color, unit=unit)
        .first()
    )
    if stock_record is None:
        raise ValueError("Недостатньо на складі: є 0")

    if stock_record.quantity < quantity_decimal:
        raise ValueError(f"Недостатньо на складі: є {stock_record.quantity}, потрібно {quantity_decimal}")

    stock_record.quantity -= quantity_decimal
    stock_record.save(update_fields=["quantity", "updated_at"])

    MaterialStockMovement.objects.create(
        stock_record=stock_record,
        quantity_change=-quantity_decimal,
        reason=reason,
        related_purchase_order_line=related_purchase_order_line,
        related_transfer=related_transfer,
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
        related_transfer=transfer,
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
        related_transfer=transfer,
        created_by=created_by,
        notes=notes,
    )

    transfer.status = MaterialStockTransfer.Status.COMPLETED
    transfer.completed_at = timezone.now()
    transfer.save(update_fields=["status", "completed_at"])
    return transfer


@transaction.atomic
def receive_purchase_order_line(
    *,
    purchase_order_line: PurchaseOrderLine,
    quantity: Decimal,
    warehouse_id: int,
    received_by: "AbstractBaseUser | None" = None,
    notes: str = "",
) -> GoodsReceiptLine:
    quantity_decimal = Decimal(str(quantity))
    if quantity_decimal <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")

    po_line = PurchaseOrderLine.objects.select_for_update().select_related(
        "purchase_order", "material", "material_color"
    ).get(pk=purchase_order_line.pk)

    if quantity_decimal > po_line.remaining_quantity:
        raise ValueError(f"Cannot receive more than remaining quantity: {po_line.remaining_quantity}")

    receipt = GoodsReceipt.objects.create(
        supplier=po_line.purchase_order.supplier,
        purchase_order=po_line.purchase_order,
        warehouse_id=warehouse_id,
        received_by=received_by,
        notes=notes,
    )
    receipt_line = GoodsReceiptLine.objects.create(
        receipt=receipt,
        purchase_order_line=po_line,
        material=po_line.material,
        material_color=po_line.material_color,
        quantity=quantity_decimal,
        unit=po_line.unit,
        unit_cost=po_line.unit_price,
        notes=notes,
    )

    add_material_stock(
        warehouse_id=warehouse_id,
        material=po_line.material,
        material_color=po_line.material_color,
        quantity=quantity_decimal,
        unit=po_line.unit,
        reason=MaterialStockMovement.Reason.PURCHASE_IN,
        related_purchase_order_line=po_line,
        related_receipt_line=receipt_line,
        created_by=received_by,
        notes=notes,
    )

    po_line.received_quantity += quantity_decimal
    po_line.save(update_fields=["received_quantity", "updated_at"])

    _update_purchase_order_status(po_line.purchase_order)
    return receipt_line


def _update_purchase_order_status(purchase_order: PurchaseOrder) -> None:
    lines = list(purchase_order.lines.all())
    if not lines:
        return

    if all(line.received_quantity >= line.quantity for line in lines):
        new_status = PurchaseOrder.Status.RECEIVED
    elif any(line.received_quantity > Decimal("0") for line in lines):
        new_status = PurchaseOrder.Status.PARTIALLY_RECEIVED
    else:
        return

    if purchase_order.status != new_status:
        purchase_order.status = new_status
        purchase_order.save(update_fields=["status", "updated_at"])
