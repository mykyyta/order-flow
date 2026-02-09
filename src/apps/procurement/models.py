"""Compatibility model exports for procurement context.

At this stage we keep physical tables in `apps.materials` and provide
new context-level imports from `apps.procurement`.
"""

from apps.materials.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierMaterialOffer,
)

SupplierOffer = SupplierMaterialOffer

__all__ = [
    "Supplier",
    "SupplierOffer",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "GoodsReceipt",
    "GoodsReceiptLine",
]
