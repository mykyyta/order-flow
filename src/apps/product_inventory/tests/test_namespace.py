import pytest

from apps.inventory.models import FinishedStockRecord, FinishedStockTransfer, WIPStockRecord
from apps.product_inventory.models import ProductStockRecord, ProductStockTransfer
from apps.product_inventory.services import (
    add_to_product_stock,
    get_product_stock_quantity,
    remove_from_product_stock,
    transfer_product_stock,
)


@pytest.mark.django_db
def test_product_inventory_models_alias_inventory_models():
    assert ProductStockRecord is FinishedStockRecord
    assert ProductStockTransfer is FinishedStockTransfer
    assert WIPStockRecord._meta.model_name == "wipstockrecord"


def test_product_inventory_services_are_exposed():
    assert callable(get_product_stock_quantity)
    assert callable(add_to_product_stock)
    assert callable(remove_from_product_stock)
    assert callable(transfer_product_stock)
