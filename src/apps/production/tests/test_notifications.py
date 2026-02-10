"""Notification tests (delayed idempotency)."""
from unittest.mock import patch

import pytest

from apps.production.models import DelayedNotificationLog
from apps.user_settings.models import NotificationSetting

from .conftest import ColorFactory, OrderFactory, ProductModelFactory, UserFactory


@pytest.mark.django_db
def test_orders_created_delayed_is_idempotent_per_user_and_order():
    from apps.production.notifications import _orders_created_delayed
    user = UserFactory(telegram_id="12345")
    NotificationSetting.objects.get_or_create(
        user=user,
        defaults={
            "notify_order_created": True,
            "notify_order_created_pause": True,
            "notify_order_finished": True,
        },
    )
    model = ProductModelFactory()
    color = ColorFactory()
    order = OrderFactory(model=model, color=color)
    with patch("apps.production.notifications.send_tg_message", return_value=True):
        _orders_created_delayed(orders=[order])
        _orders_created_delayed(orders=[order])
    assert DelayedNotificationLog.objects.filter(user=user, order=order).count() == 1
