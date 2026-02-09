import pytest

from apps.orders.models import Order, OrderStatusHistory
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


@pytest.mark.django_db
def test_production_models_alias_legacy_order_models():
    assert ProductionOrder is Order
    assert ProductionOrderStatusHistory is OrderStatusHistory
