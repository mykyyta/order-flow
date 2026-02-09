from apps.material_inventory.services import add_material_stock, remove_material_stock
from apps.procurement.services import receive_purchase_order_line

from apps.materials.procurement_services import (
    add_material_stock as legacy_add_material_stock,
    receive_purchase_order_line as legacy_receive_purchase_order_line,
    remove_material_stock as legacy_remove_material_stock,
)


def test_legacy_procurement_services_exports_new_context_callables():
    assert legacy_add_material_stock is add_material_stock
    assert legacy_remove_material_stock is remove_material_stock
    assert legacy_receive_purchase_order_line is receive_purchase_order_line
