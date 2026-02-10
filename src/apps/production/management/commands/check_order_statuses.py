from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery

from apps.production.domain.status import STATUS_FINISHED
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


class Command(BaseCommand):
    help = "Check and optionally fix ProductionOrder.current_status against latest history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Apply fixes to current_status where possible.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of orders checked (for sampling).",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        limit = options["limit"]

        latest_status_subq = (
            ProductionOrderStatusHistory.objects.filter(order_id=OuterRef("pk"))
            .order_by("-id")
            .values("new_status")[:1]
        )

        orders = ProductionOrder.objects.annotate(latest_status=Subquery(latest_status_subq)).only(
            "id", "current_status", "finished_at"
        )

        if limit:
            orders = orders[:limit]

        mismatches = 0
        fixed = 0
        missing_history = 0

        for order in orders:
            expected = order.latest_status
            if not expected:
                if order.finished_at is not None:
                    expected = STATUS_FINISHED
                else:
                    missing_history += 1
                    continue

            if order.current_status != expected:
                mismatches += 1
                if fix:
                    ProductionOrder.objects.filter(id=order.id).update(current_status=expected)
                    fixed += 1

        self.stdout.write(f"Checked orders: {orders.count()}")
        self.stdout.write(f"Missing history: {missing_history}")
        self.stdout.write(f"Mismatches: {mismatches}")
        if fix:
            self.stdout.write(f"Fixed: {fixed}")
        else:
            self.stdout.write("Run with --fix to apply updates.")
