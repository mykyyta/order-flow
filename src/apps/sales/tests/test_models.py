import pytest

from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineComponentSelection


@pytest.mark.django_db
def test_sales_models_are_concrete_v2_models():
    assert SalesOrder._meta.label == "sales.SalesOrder"
    assert SalesOrderLine._meta.label == "sales.SalesOrderLine"
    assert SalesOrderLineComponentSelection._meta.label == "sales.SalesOrderLineComponentSelection"
    assert SalesOrder._meta.proxy is False
    assert SalesOrderLine._meta.proxy is False
    assert SalesOrderLineComponentSelection._meta.proxy is False
