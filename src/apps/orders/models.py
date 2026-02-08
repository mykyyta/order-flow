from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from config import settings
from apps.orders.domain.order_statuses import (
    STATUS_FINISHED,
    STATUS_NEW,
    get_allowed_transitions,
    status_choices,
)
from apps.orders.exceptions import InvalidStatusTransition

STATUS_CHOICES = status_choices(include_legacy=True, include_terminal=True)


class CustomUser(AbstractUser):
    telegram_id = models.CharField(
        max_length=50, blank=True, null=True, unique=True, verbose_name="Telegram ID"
    )

    def __str__(self):
        return self.username


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.ForeignKey("catalog.ProductModel", on_delete=models.CASCADE)
    color = models.ForeignKey("catalog.Color", on_delete=models.CASCADE)
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

    def get_status(self):
        return self.current_status

    def get_status_display(self):
        return self.get_current_status_display()

    def can_transition_to(self, new_status: str) -> bool:
        allowed = get_allowed_transitions(self.current_status)
        return new_status in allowed

    def transition_to(self, new_status: str, changed_by: "CustomUser") -> None:
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransition(self.current_status, new_status)
        self.current_status = new_status
        self.finished_at = self._compute_finished_at(new_status)
        OrderStatusHistory.objects.create(
            order=self,
            new_status=new_status,
            changed_by=changed_by,
        )

    def _compute_finished_at(self, new_status: str):
        if new_status == STATUS_FINISHED:
            return timezone.now()
        return None

    def __str__(self):
        return f"{self.model.name} ({self.color.name}) - {self.get_status()}"

    class Meta:
        indexes = [
            models.Index(
                fields=["current_status", "-finished_at"],
                name="orders_completed_idx",
            ),
        ]


class OrderStatusHistory(models.Model):
    STATUS_CHOICES = STATUS_CHOICES

    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} → {self.new_status} ({self.changed_at})"

    class Meta:
        indexes = [
            models.Index(fields=["order", "changed_at"]),
        ]


class DelayedNotificationLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delayed_notification_logs",
    )
    order = models.ForeignKey(
        Order,
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
