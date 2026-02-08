from django.conf import settings
from django.db import models


class NotificationSetting(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    notify_order_created = models.BooleanField(default=True)
    notify_order_finished = models.BooleanField(default=True)
    notify_order_created_pause = models.BooleanField(default=True)
