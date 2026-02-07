from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from orders.application.ports import Clock, NotificationSender, OrderRepository
from orders.domain.policies import compute_finished_at
from orders.application.exceptions import InvalidStatusTransition
from orders.domain.status import STATUS_FINISHED, STATUS_NEW, validate_status
from orders.domain.transitions import is_transition_allowed


@dataclass
class OrderService:
    repo: OrderRepository
    notifier: NotificationSender
    clock: Clock

    def create_order(
        self,
        *,
        model,
        color,
        embroidery: bool,
        urgent: bool,
        etsy: bool,
        comment: Optional[str],
        created_by,
        orders_url: Optional[str],
    ):
        order = self.repo.create_order(
            model=model,
            color=color,
            embroidery=embroidery,
            urgent=urgent,
            etsy=etsy,
            comment=comment,
        )
        self.repo.add_status(order=order, new_status=STATUS_NEW, changed_by=created_by)
        self.repo.set_current_status(order=order, current_status=STATUS_NEW)
        self.notifier.order_created(order=order, orders_url=orders_url)
        return order

    def change_status(
        self,
        *,
        orders: Iterable,
        new_status: str,
        changed_by,
    ) -> None:
        normalized_status = validate_status(new_status)
        now = self.clock.now()

        for order in orders:
            latest_status = self.repo.get_latest_status(order=order)
            if latest_status is None and order.current_status:
                latest_status = order.current_status
            desired_finished_at = compute_finished_at(
                current_finished_at=order.finished_at,
                new_status=normalized_status,
                now=now,
            )

            if latest_status == normalized_status:
                if order.current_status != normalized_status:
                    self.repo.set_current_status(
                        order=order,
                        current_status=normalized_status,
                    )
                if order.finished_at != desired_finished_at:
                    self.repo.set_finished_at(order=order, finished_at=desired_finished_at)
                continue

            if latest_status is not None and not is_transition_allowed(
                latest_status, normalized_status
            ):
                raise InvalidStatusTransition(latest_status, normalized_status)

            self.repo.add_status(order=order, new_status=normalized_status, changed_by=changed_by)
            self.repo.set_current_status(order=order, current_status=normalized_status)
            self.repo.set_finished_at(order=order, finished_at=desired_finished_at)

            if normalized_status == STATUS_FINISHED:
                self.notifier.order_finished(order=order)
