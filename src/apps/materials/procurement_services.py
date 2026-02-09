"""Compatibility exports for legacy imports.

Preferred import paths:
- apps.procurement.services.receive_purchase_order_line
- apps.material_inventory.services.add_material_stock / remove_material_stock
"""

from apps.material_inventory.services import add_material_stock, remove_material_stock
from apps.procurement.services import receive_purchase_order_line

__all__ = [
    "add_material_stock",
    "remove_material_stock",
    "receive_purchase_order_line",
]
