from apps.sales.domain.status import (
    PRODUCTION_STATUS_DONE,
    STATUS_NEW,
    STATUS_READY,
)
from apps.sales.models import SalesOrder, SalesOrderLine


def test_sales_domain_exposes_customer_order_status_codes():
    assert STATUS_NEW == SalesOrder.Status.NEW
    assert STATUS_READY == SalesOrder.Status.READY
    assert PRODUCTION_STATUS_DONE == SalesOrderLine.ProductionStatus.DONE
