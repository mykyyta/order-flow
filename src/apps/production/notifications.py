"""Production order notification helpers (Telegram)."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from django.utils.timezone import localtime, now

from apps.production.models import DelayedNotificationLog, ProductionOrder
from apps.production.utils import generate_order_details, send_tg_message
from apps.user_settings.models import NotificationSetting

if TYPE_CHECKING:
    from apps.production.models import ProductionOrder

logger = logging.getLogger(__name__)


def send_order_created(*, order: "ProductionOrder", orders_url: str | None) -> None:
    users_to_notify = NotificationSetting.objects.filter(
        notify_order_created=True,
        user__telegram_id__isnull=False,
    ).select_related("user")

    if not users_to_notify.exists():
        logger.info("Order created notifications skipped: no users")
        return

    order_details = generate_order_details(order)
    message = f"+ {order_details}"
    if orders_url:
        message += f"\n{orders_url}\n"

    for setting in users_to_notify:
        if setting.notify_order_created_pause:
            current_hour = localtime(now()).hour
            if current_hour < 8 or current_hour >= 18:
                logger.info(
                    "Order created notification skipped (outside hours) user_id=%s order_id=%s",
                    setting.user_id,
                    order.id,
                )
                continue
        sent = send_tg_message(setting.user.telegram_id, message)
        if sent:
            logger.info(
                "Order created notification sent user_id=%s order_id=%s",
                setting.user_id,
                order.id,
            )
        else:
            logger.warning(
                "Order created notification failed user_id=%s order_id=%s",
                setting.user_id,
                order.id,
            )


def send_order_finished(*, order: "ProductionOrder") -> None:
    users_to_notify = NotificationSetting.objects.filter(
        notify_order_finished=True,
    ).select_related("user")

    for setting in users_to_notify:
        user = setting.user
        if user.telegram_id:
            color_name = "-"
            if order.variant and order.variant.color:
                color_name = order.variant.color.name
            message = f"Замовлення завершено: {order.product.name}, {color_name}."
            sent = send_tg_message(user.telegram_id, message)
            if sent:
                logger.info(
                    "Order finished notification sent user_id=%s order_id=%s",
                    setting.user_id,
                    order.id,
                )
            else:
                logger.warning(
                    "Order finished notification failed user_id=%s order_id=%s",
                    setting.user_id,
                    order.id,
                )


def send_delayed_order_created_notifications() -> str:
    """Send order-created notifications for orders created 18:00–08:00. Returns status message."""
    current_time = now()
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
    orders = list(
        ProductionOrder.objects.filter(
            created_at__gte=yesterday_18,
            created_at__lt=today_08,
        )
    )
    if not orders:
        return "no orders to notify"
    sent = _orders_created_delayed(orders=orders)
    if not sent:
        return "no users to notify"
    return "delayed notifications sent"


def _orders_created_delayed(*, orders: list["ProductionOrder"]) -> bool:
    users_to_notify = NotificationSetting.objects.filter(
        notify_order_created=True,
        notify_order_created_pause=True,
        user__telegram_id__isnull=False,
    ).select_related("user")

    if not users_to_notify.exists():
        logger.info("Delayed notifications skipped: no users")
        return False

    order_ids = [o.id for o in orders]
    for setting in users_to_notify:
        notified_order_ids = set(
            DelayedNotificationLog.objects.filter(
                user_id=setting.user_id,
                order_id__in=order_ids,
            ).values_list("order_id", flat=True)
        )
        pending_orders = [o for o in orders if o.id not in notified_order_ids]
        if not pending_orders:
            logger.info(
                "Delayed notifications skipped (already sent) user_id=%s orders=%s",
                setting.user_id,
                len(orders),
            )
            continue

        user_orders = []
        for order in pending_orders:
            order_details = generate_order_details(order)
            user_orders.append(f"+ {order_details}")

        if user_orders:
            message = "\n".join(user_orders)
            sent = send_tg_message(setting.user.telegram_id, message)
            if sent:
                DelayedNotificationLog.objects.bulk_create(
                    [
                        DelayedNotificationLog(user_id=setting.user_id, order_id=order.id)
                        for order in pending_orders
                    ],
                    ignore_conflicts=True,
                )
                logger.info(
                    "Delayed notifications sent user_id=%s orders=%s",
                    setting.user_id,
                    len(user_orders),
                )
            else:
                logger.warning(
                    "Delayed notifications failed user_id=%s orders=%s",
                    setting.user_id,
                    len(user_orders),
                )
    return True
