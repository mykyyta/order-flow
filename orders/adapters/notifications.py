from __future__ import annotations

import logging
from typing import Optional

from django.utils.timezone import localtime, now

from orders.models import NotificationSetting
from orders.utils import generate_order_details, send_tg_message

logger = logging.getLogger(__name__)


class DjangoNotificationSender:
    def order_created(self, *, order, orders_url: Optional[str]) -> None:
        users_to_notify = (
            NotificationSetting.objects.filter(
                notify_order_created=True,
                user__telegram_id__isnull=False,
            )
            .select_related("user")
        )

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
                working_hours_start = 8
                working_hours_end = 18
                if current_hour < working_hours_start or current_hour >= working_hours_end:
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

    def order_finished(self, *, order) -> None:
        users_to_notify = NotificationSetting.objects.filter(
            notify_order_finished=True
        ).select_related("user")

        for setting in users_to_notify:
            user = setting.user
            if user.telegram_id:
                message = f"Замовлення завершено: {order.model.name}, {order.color.name}."
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

    def orders_created_delayed(self, *, orders) -> bool:
        users_to_notify = NotificationSetting.objects.filter(
            notify_order_created=True,
            notify_order_created_pause=True,
            user__telegram_id__isnull=False,
        ).select_related("user")

        if not users_to_notify.exists():
            logger.info("Delayed notifications skipped: no users")
            return False

        for setting in users_to_notify:
            user_orders = []
            for order in orders:
                order_details = generate_order_details(order)
                user_orders.append(f"+ {order_details}")

            if user_orders:
                message = "\n".join(user_orders)
                sent = send_tg_message(setting.user.telegram_id, message)
                if sent:
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
