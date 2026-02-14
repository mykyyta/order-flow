"""Generate sample products, primary colors, and production orders for local development."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Product
from apps.catalog.variants import resolve_or_create_variant
from apps.materials.models import Material, MaterialColor, MaterialUnit
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
    help = "Generate sample products, primary colors, and production orders for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=15,
            help="Number of orders to create (default: 15)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        primary_material = self._ensure_primary_colors()
        self._ensure_products(primary_material=primary_material)
        created = self._create_orders(count=count, primary_material=primary_material)
        self.stdout.write(self.style.SUCCESS(f"Created {created} sample orders."))

    def _ensure_products(self, *, primary_material: Material) -> None:
        products_data = [
            "Сумка клатч",
            "Сумка на плече",
            "Рюкзак",
            "Гаманець",
            "Косметичка",
        ]
        for name in products_data:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={"primary_material": primary_material},
            )
            if product.primary_material_id is None:
                product.primary_material = primary_material
                product.save(update_fields=["primary_material"])
        self.stdout.write(f"Ensured {len(products_data)} products.")

    def _ensure_primary_colors(self) -> Material:
        material, _ = Material.objects.get_or_create(
            name="Повсть",
            defaults={"stock_unit": MaterialUnit.SQUARE_METER},
        )
        if not material.stock_unit:
            material.stock_unit = MaterialUnit.SQUARE_METER
            material.save(update_fields=["stock_unit", "updated_at"])
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
            MaterialColor.objects.get_or_create(
                material=material,
                code=code,
                defaults={"name": name},
            )
        self.stdout.write(f"Ensured {len(colors_data)} primary colors.")
        return material

    def _create_orders(self, *, count: int, primary_material: Material) -> int:
        products = list(Product.objects.filter(archived_at__isnull=True).order_by("id"))
        colors = list(
            MaterialColor.objects.filter(
                material=primary_material,
                archived_at__isnull=True,
            ).order_by("name")
        )
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
            self.stdout.write(self.style.WARNING("No products or primary colors found."))
            return 0

        created = 0
        for i in range(count):
            product = products[i % len(products)]
            color = colors[i % len(colors)]
            status = statuses[i % len(statuses)]
            comment = comments[i % len(comments)]
            variant = resolve_or_create_variant(
                product_id=product.id,
                primary_material_color_id=color.id,
            )

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
