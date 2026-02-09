from apps.customer_orders.models import CustomerOrder, CustomerOrderLine
from apps.sales.domain.status import (
    PRODUCTION_STATUS_DONE,
    STATUS_NEW,
    STATUS_READY,
)


def test_sales_domain_exposes_customer_order_status_codes():
    assert STATUS_NEW == CustomerOrder.Status.NEW
    assert STATUS_READY == CustomerOrder.Status.READY
    assert PRODUCTION_STATUS_DONE == CustomerOrderLine.ProductionStatus.DONE
