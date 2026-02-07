from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol


class OrderRepository(Protocol):
    def create_order(
        self,
        *,
        model,
        color,
        embroidery: bool,
        urgent: bool,
        etsy: bool,
        comment: Optional[str],
    ):
        ...

    def add_status(self, *, order, new_status: str, changed_by) -> None:
        ...

    def get_latest_status(self, *, order) -> Optional[str]:
        ...

    def set_finished_at(self, *, order, finished_at: Optional[datetime]) -> None:
        ...

    def set_current_status(self, *, order, current_status: str) -> None:
        ...

    def list_orders_created_between(self, *, start: datetime, end: datetime):
        ...


class NotificationSender(Protocol):
    def order_created(self, *, order, orders_url: Optional[str]) -> None:
        ...

    def order_finished(self, *, order) -> None:
        ...

    def orders_created_delayed(self, *, orders) -> bool:
        ...


class Clock(Protocol):
    def now(self) -> datetime:
        ...
