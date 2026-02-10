"""Generate sample products, colors, and production orders for local development."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Color, Product
from apps.catalog.variants import resolve_or_create_variant
from apps.production.domain.status import (
    STATUS_BLOCKED,
    STATUS_DECIDING,
    STATUS_DONE,
    STATUS_EMBROIDERY,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
)
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


class Command(BaseCommand):
    help = "Generate sample products, colors, and production orders for development."

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
        products_data = [
            "Сумка клатч",
            "Сумка на плече",
            "Рюкзак",
            "Гаманець",
            "Косметичка",
        ]
        for name in products_data:
            Product.objects.get_or_create(name=name)
        self.stdout.write(f"Ensured {len(products_data)} products.")

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
        products = list(Product.objects.filter(archived_at__isnull=True).order_by("id"))
        colors = list(Color.objects.all())
        statuses = [
            STATUS_NEW,
            STATUS_NEW,
            STATUS_IN_PROGRESS,
            STATUS_EMBROIDERY,
            STATUS_DECIDING,
            STATUS_BLOCKED,
            STATUS_DONE,
        ]
        comments = [
            "",
            "Доставка кур'єром",
            "Подарункова упаковка",
            "Два примірники",
            None,
        ]

        if not products or not colors:
            self.stdout.write(self.style.WARNING("No products or colors found."))
            return 0

        created = 0
        for i in range(count):
            product = products[i % len(products)]
            color = colors[i % len(colors)]
            status = statuses[i % len(statuses)]
            comment = comments[i % len(comments)]
            variant = resolve_or_create_variant(product_id=product.id, color_id=color.id)

            order = ProductionOrder.objects.create(
                product=product,
                variant=variant,
                is_embroidery=(i % 3 == 0),
                comment=comment or "",
                is_urgent=(i % 5 == 0),
                is_etsy=(i % 7 == 0),
                status=status,
                finished_at=timezone.now() if status == STATUS_DONE else None,
            )
            ProductionOrderStatusHistory.objects.create(
                order=order,
                new_status=status,
                changed_by=None,
            )
            created += 1

        return created
