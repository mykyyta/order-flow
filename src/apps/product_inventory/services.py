"""Compatibility services for product inventory context.

Business logic remains implemented in `apps.inventory.services`.
"""

from __future__ import annotations

from apps.inventory.services import (
    add_to_stock,
    add_to_wip_stock,
    get_stock_quantity,
    get_wip_stock_quantity,
    remove_from_stock,
    remove_from_wip_stock,
    transfer_finished_stock,
)

get_product_stock_quantity = get_stock_quantity
add_to_product_stock = add_to_stock
remove_from_product_stock = remove_from_stock
transfer_product_stock = transfer_finished_stock

__all__ = [
    "get_product_stock_quantity",
    "add_to_product_stock",
    "remove_from_product_stock",
    "transfer_product_stock",
    "get_wip_stock_quantity",
    "add_to_wip_stock",
    "remove_from_wip_stock",
]
