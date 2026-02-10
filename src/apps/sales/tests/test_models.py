import pytest

from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineComponentSelection


@pytest.mark.django_db
def test_sales_models_alias_legacy_customer_order_models():
    assert SalesOrderLine._meta.model_name == "customerorderline"
    assert SalesOrder._meta.model_name == "customerorder"
    assert SalesOrderLineComponentSelection._meta.model_name == "customerorderlinecomponent"
