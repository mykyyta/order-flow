"""Compatibility model exports for product inventory context.

Physical tables remain in `apps.inventory`; this module provides a clearer
domain entrypoint for finished goods inventory.
"""

from apps.inventory.models import (
    FinishedStockMovement,
    FinishedStockRecord,
    FinishedStockTransfer,
    FinishedStockTransferLine,
    WIPStockMovement,
    WIPStockRecord,
)

ProductStockRecord = FinishedStockRecord
ProductStockMovement = FinishedStockMovement
ProductStockTransfer = FinishedStockTransfer
ProductStockTransferLine = FinishedStockTransferLine

__all__ = [
    "ProductStockRecord",
    "ProductStockMovement",
    "ProductStockTransfer",
    "ProductStockTransferLine",
    "WIPStockRecord",
    "WIPStockMovement",
]
