from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from orders.application.ports import Clock, NotificationSender, OrderRepository


@dataclass
class DelayedNotificationService:
    repo: OrderRepository
    notifier: NotificationSender
    clock: Clock

    def send_delayed_notifications(self) -> str:
        current_time = self.clock.now()
        today = current_time.date()

        yesterday_18 = datetime.combine(
            today - timedelta(days=1),
            time(hour=18),
            tzinfo=current_time.tzinfo,
        )
        today_08 = datetime.combine(
            today,
            time(hour=8),
            tzinfo=current_time.tzinfo,
        )

        orders = self.repo.list_orders_created_between(
            start=yesterday_18,
            end=today_08,
        )

        if not orders:
            return "no orders to notify"

        sent = self.notifier.orders_created_delayed(orders=orders)
        if not sent:
            return "no users to notify"

        return "delayed notifications sent"
