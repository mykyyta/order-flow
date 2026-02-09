"""Compatibility model exports for sales context."""

from apps.customer_orders.models import CustomerOrder, CustomerOrderLine, CustomerOrderLineComponent

SalesOrder = CustomerOrder
SalesOrderLine = CustomerOrderLine
SalesOrderLineComponentSelection = CustomerOrderLineComponent

__all__ = [
    "SalesOrder",
    "SalesOrderLine",
    "SalesOrderLineComponentSelection",
]
