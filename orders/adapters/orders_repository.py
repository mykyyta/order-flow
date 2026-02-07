from __future__ import annotations

from typing import Optional

from orders.models import Order, OrderStatusHistory


class DjangoOrderRepository:
    def create_order(
        self,
        *,
        model,
        color,
        embroidery: bool,
        urgent: bool,
        etsy: bool,
        comment: Optional[str],
    ) -> Order:
        return Order.objects.create(
            model=model,
            color=color,
            embroidery=embroidery,
            urgent=urgent,
            etsy=etsy,
            comment=comment,
        )

    def add_status(self, *, order: Order, new_status: str, changed_by) -> None:
        OrderStatusHistory.objects.create(
            order=order,
            new_status=new_status,
            changed_by=changed_by,
        )

    def get_latest_status(self, *, order: Order) -> Optional[str]:
        latest_status = OrderStatusHistory.objects.filter(order=order).order_by("-id").first()
        return latest_status.new_status if latest_status else None

    def set_finished_at(self, *, order: Order, finished_at) -> None:
        order.finished_at = finished_at
        order.save(update_fields=["finished_at"])

    def set_current_status(self, *, order: Order, current_status: str) -> None:
        order.current_status = current_status
        order.save(update_fields=["current_status"])

    def list_orders_created_between(self, *, start, end):
        return list(Order.objects.filter(created_at__gte=start, created_at__lt=end))
