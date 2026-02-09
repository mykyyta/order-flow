"""Compatibility model exports for production context."""

from apps.orders.models import Order, OrderStatusHistory

ProductionOrder = Order
ProductionOrderStatusHistory = OrderStatusHistory

__all__ = [
    "ProductionOrder",
    "ProductionOrderStatusHistory",
]
