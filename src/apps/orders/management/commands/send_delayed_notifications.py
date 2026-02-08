from django.core.management.base import BaseCommand

from apps.orders.notifications import send_delayed_order_created_notifications


class Command(BaseCommand):
    help = "Send delayed order notifications for after-hours orders."

    def handle(self, *args, **options):
        status = send_delayed_order_created_notifications()
        self.stdout.write(status)
