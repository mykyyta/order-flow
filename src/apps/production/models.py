from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from config import settings

from apps.catalog.variants import product_variant_matches_legacy_fields
from apps.production.exceptions import InvalidStatusTransition
from apps.production.domain.order_statuses import (
    STATUS_FINISHED,
    STATUS_NEW,
    get_allowed_transitions,
    status_choices,
)

STATUS_CHOICES = status_choices(include_legacy=True, include_terminal=True)

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser
    from apps.sales.models import SalesOrderLine


class ProductionOrder(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.ForeignKey("catalog.ProductModel", on_delete=models.PROTECT)
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_orders",
    )
    color = models.ForeignKey("catalog.Color", on_delete=models.PROTECT, null=True, blank=True)
    primary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_orders_primary_colors",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_orders_secondary_colors",
    )
    embroidery = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    urgent = models.BooleanField(default=False)
    etsy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    current_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        db_index=True,
    )
    customer_order_line = models.ForeignKey(
        "sales.SalesOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_orders",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["current_status", "-finished_at"],
                name="prod_order_completed_idx",
            ),
        ]

    @property
    def sales_order_line_id(self) -> int | None:
        return self.customer_order_line_id

    @property
    def sales_order_line(self) -> SalesOrderLine | None:
        return self.customer_order_line

    def get_status(self) -> str:
        return self.current_status

    def get_status_display(self) -> str:
        return self.get_current_status_display()

    def can_transition_to(self, new_status: str) -> bool:
        allowed = get_allowed_transitions(self.current_status)
        return new_status in allowed

    def transition_to(self, new_status: str, changed_by: CustomUser) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransition(self.current_status, new_status)
        self.current_status = new_status
        self.finished_at = self._compute_finished_at(new_status)
        ProductionOrderStatusHistory.objects.create(
            order=self,
            new_status=new_status,
            changed_by=changed_by,
        )

    def _compute_finished_at(self, new_status: str) -> datetime | None:
        if new_status == STATUS_FINISHED:
            return timezone.now()
        return None

    def __str__(self) -> str:
        if self.primary_material_color:
            color_name = self.primary_material_color.name
            if self.secondary_material_color:
                color_name = f"{color_name} / {self.secondary_material_color.name}"
        elif self.color:
            color_name = self.color.name
        else:
            color_name = "custom"
        return f"{self.model.name} ({color_name}) - {self.get_status()}"

    def _validate_product_variant_consistency(self) -> None:
        if self.product_variant_id is None:
            return

        if not product_variant_matches_legacy_fields(
            product_variant=self.product_variant,
            product_model_id=self.model_id,
            color_id=self.color_id,
            primary_material_color_id=self.primary_material_color_id,
            secondary_material_color_id=self.secondary_material_color_id,
        ):
            raise ValidationError(
                {"product_variant": "Product variant must match model/color/material colors fields."}
            )

    def save(self, *args, **kwargs) -> None:
        self._validate_product_variant_consistency()
        super().save(*args, **kwargs)


class ProductionOrderStatusHistory(models.Model):
    STATUS_CHOICES = STATUS_CHOICES

    id = models.AutoField(primary_key=True)
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


Order = ProductionOrder
OrderStatusHistory = ProductionOrderStatusHistory
