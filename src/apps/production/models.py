from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from config import settings

from apps.production.domain.order_statuses import (
    STATUS_DONE,
    STATUS_NEW,
    get_allowed_transitions,
    status_choices,
)
from apps.production.exceptions import InvalidStatusTransition

STATUS_CHOICES = status_choices(include_legacy=True, include_terminal=True)

if TYPE_CHECKING:
    from apps.accounts.models import User


class ProductionOrder(models.Model):
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_orders",
    )
    is_embroidery = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    is_urgent = models.BooleanField(default=False)
    is_etsy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        db_index=True,
    )
    sales_order_line = models.ForeignKey(
        "sales.SalesOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_orders",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["status", "-finished_at"],
                name="prod_order_completed_idx",
            ),
        ]

    def get_status(self) -> str:
        return self.status

    def can_transition_to(self, new_status: str) -> bool:
        allowed = get_allowed_transitions(self.status)
        return new_status in allowed

    def transition_to(self, new_status: str, changed_by: User) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransition(self.status, new_status)
        self.status = new_status
        self.finished_at = self._compute_finished_at(new_status)
        ProductionOrderStatusHistory.objects.create(
            order=self,
            new_status=new_status,
            changed_by=changed_by,
        )

    def _compute_finished_at(self, new_status: str) -> datetime | None:
        if new_status == STATUS_DONE:
            return timezone.now()
        return None

    def __str__(self) -> str:
        if self.variant_id:
            return f"{self.variant} - {self.get_status()}"
        return f"{self.product.name} - {self.get_status()}"


class ProductionOrderStatusHistory(models.Model):
    STATUS_CHOICES = STATUS_CHOICES

    order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="history",
    )
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "changed_at"]),
        ]

    @property
    def production_order_id(self) -> int:
        return self.order_id

    def __str__(self) -> str:
        return f"{self.order_id} -> {self.new_status} ({self.changed_at})"


class DelayedNotificationLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delayed_notification_logs",
    )
    order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="delayed_notification_logs",
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "order"],
                name="orders_delayed_notification_user_order_uniq",
            )
        ]
