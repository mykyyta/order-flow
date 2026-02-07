from __future__ import annotations

from django.core.management.base import BaseCommand

from orders.adapters.clock import DjangoClock
from orders.adapters.notifications import DjangoNotificationSender
from orders.adapters.orders_repository import DjangoOrderRepository
from orders.application.notification_service import DelayedNotificationService


class Command(BaseCommand):
    help = "Send delayed order notifications for after-hours orders."

    def handle(self, *args, **options):
        service = DelayedNotificationService(
            repo=DjangoOrderRepository(),
            notifier=DjangoNotificationSender(),
            clock=DjangoClock(),
        )
        status = service.send_delayed_notifications()
        self.stdout.write(status)
