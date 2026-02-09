import pytest

from apps.customer_orders.models import CustomerOrder, CustomerOrderLine, CustomerOrderLineComponent
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineComponentSelection


@pytest.mark.django_db
def test_sales_models_alias_legacy_customer_order_models():
    assert SalesOrder is CustomerOrder
    assert SalesOrderLine is CustomerOrderLine
    assert SalesOrderLineComponentSelection is CustomerOrderLineComponent
