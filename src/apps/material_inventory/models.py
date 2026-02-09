"""Compatibility model exports for material inventory context.

At this stage we keep physical tables in `apps.materials` and provide
new context-level imports from `apps.material_inventory`.
"""

from apps.materials.models import (
    MaterialMovement,
    MaterialStockRecord,
    MaterialStockTransfer,
    MaterialStockTransferLine,
)

MaterialStockMovement = MaterialMovement

__all__ = [
    "MaterialStockRecord",
    "MaterialStockMovement",
    "MaterialStockTransfer",
    "MaterialStockTransferLine",
]
