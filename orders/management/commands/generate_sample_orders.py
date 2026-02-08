"""Generate sample product models, colors, and orders for local development."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.domain.status import (
    STATUS_ALMOST_FINISHED,
    STATUS_EMBROIDERY,
    STATUS_FINISHED,
    STATUS_NEW,
    STATUS_ON_HOLD,
)
from catalog.models import Color, ProductModel
from orders.models import Order


class Command(BaseCommand):
    help = "Generate sample product models, colors, and orders for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=15,
            help="Number of orders to create (default: 15)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        self._ensure_products()
        self._ensure_colors()
        created = self._create_orders(count)
        self.stdout.write(self.style.SUCCESS(f"Created {created} sample orders."))

    def _ensure_products(self) -> None:
        models_data = [
            "Сумка клатч",
            "Сумка на плече",
            "Рюкзак",
            "Гаманець",
            "Косметичка",
        ]
        for name in models_data:
            ProductModel.objects.get_or_create(name=name)
        self.stdout.write(f"Ensured {len(models_data)} product models.")

    def _ensure_colors(self) -> None:
        colors_data = [
            ("Чорний", 1001),
            ("Білий", 1002),
            ("Синій", 1003),
            ("Червоний", 1004),
            ("Зелений", 1005),
            ("Бежевий", 1006),
            ("Коричневий", 1007),
        ]
        for name, code in colors_data:
            Color.objects.get_or_create(code=code, defaults={"name": name})
        self.stdout.write(f"Ensured {len(colors_data)} colors.")

    def _create_orders(self, count: int) -> int:
        models = list(ProductModel.objects.all())
        colors = list(Color.objects.all())
        statuses = [
            STATUS_NEW,
            STATUS_NEW,
            STATUS_EMBROIDERY,
            STATUS_EMBROIDERY,
            STATUS_ALMOST_FINISHED,
            STATUS_FINISHED,
            STATUS_ON_HOLD,
        ]
        comments = [
            "",
            "Доставка кур'єром",
            "Подарункова упаковка",
            "Два примірники",
            None,
        ]

        if not models or not colors:
            self.stdout.write(self.style.WARNING("No product models or colors found."))
            return 0

        created = 0
        for i in range(count):
            model = models[i % len(models)]
            color = colors[i % len(colors)]
            status = statuses[i % len(statuses)]
            comment = comments[i % len(comments)]

            order = Order.objects.create(
                model=model,
                color=color,
                embroidery=(i % 3 == 0),
                comment=comment or "",
                urgent=(i % 5 == 0),
                etsy=(i % 7 == 0),
                current_status=status,
            )
            if status == STATUS_FINISHED:
                order.finished_at = timezone.now()
                order.save(update_fields=["finished_at"])
            created += 1

        return created
