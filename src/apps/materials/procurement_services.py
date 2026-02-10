"""Compatibility exports for legacy imports.

Preferred import paths:
- apps.procurement.services.receive_purchase_order_line
- apps.material_inventory.services.add_material_stock / remove_material_stock
"""

from apps.cutover import LegacyWritesFrozenError, ensure_legacy_writes_allowed
from apps.material_inventory.services import add_material_stock as _add_material_stock
from apps.material_inventory.services import remove_material_stock as _remove_material_stock
from apps.procurement.services import receive_purchase_order_line as _receive_purchase_order_line


def _ensure_legacy_writes_allowed() -> None:
    ensure_legacy_writes_allowed(
        operation="materials.procurement_services",
        via_v2_context=False,
    )


def add_material_stock(*args, **kwargs):
    _ensure_legacy_writes_allowed()
    return _add_material_stock(*args, **kwargs)


def remove_material_stock(*args, **kwargs):
    _ensure_legacy_writes_allowed()
    return _remove_material_stock(*args, **kwargs)


def receive_purchase_order_line(*args, **kwargs):
    _ensure_legacy_writes_allowed()
    return _receive_purchase_order_line(*args, **kwargs)

__all__ = [
    "LegacyWritesFrozenError",
    "add_material_stock",
    "remove_material_stock",
    "receive_purchase_order_line",
]
