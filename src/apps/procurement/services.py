from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.material_inventory.models import MaterialStockMovement
from apps.material_inventory.services import add_material_stock
from apps.procurement.models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine
from apps.warehouses.services import resolve_warehouse_id

if TYPE_CHECKING:
    from apps.orders.models import CustomUser


@transaction.atomic
def receive_purchase_order_line(
    *,
    purchase_order_line: PurchaseOrderLine,
    quantity: Decimal,
    warehouse_id: int | None = None,
    received_by: "CustomUser | None" = None,
    notes: str = "",
) -> GoodsReceiptLine:
    resolved_warehouse_id = resolve_warehouse_id(warehouse_id=warehouse_id)
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
        warehouse_id=resolved_warehouse_id,
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
        warehouse_id=resolved_warehouse_id,
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
