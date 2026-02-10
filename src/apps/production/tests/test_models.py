import pytest

from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


@pytest.mark.django_db
def test_production_models_alias_legacy_order_models():
    assert ProductionOrder._meta.model_name == "order"
    assert ProductionOrderStatusHistory._meta.model_name == "orderstatushistory"
