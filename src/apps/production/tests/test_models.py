import pytest

from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


@pytest.mark.django_db
def test_production_models_are_concrete_v2_models():
    assert ProductionOrder._meta.label == "production.ProductionOrder"
    assert ProductionOrderStatusHistory._meta.label == "production.ProductionOrderStatusHistory"
    assert ProductionOrder._meta.proxy is False
    assert ProductionOrderStatusHistory._meta.proxy is False
