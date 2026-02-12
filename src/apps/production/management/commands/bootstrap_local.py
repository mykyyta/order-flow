"""Bootstrap minimal local data for manual production-flow testing."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.catalog.models import Product
from apps.materials.models import Material, MaterialColor
from apps.user_settings.models import NotificationSetting


class Command(BaseCommand):
    help = "Create local admin user, base catalog, and optional sample production orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="local_admin",
            help="Admin username for local login (default: local_admin).",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="local-pass-12345",
            help="Admin password for local login.",
        )
        parser.add_argument(
            "--orders",
            type=int,
            default=10,
            help="How many sample production orders to create (default: 10).",
        )

    def handle(self, *args, **options):
        username: str = options["username"]
        password: str = options["password"]
        orders_count: int = options["orders"]

        user, created = self._ensure_admin_user(username=username, password=password)
        NotificationSetting.objects.get_or_create(user=user)
        self._ensure_catalog()

        if orders_count > 0:
            call_command("generate_sample_orders", "--count", str(orders_count), stdout=self.stdout)
        else:
            self.stdout.write("Skipped sample orders (--orders 0).")

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} local admin user: {username}"))
        self.stdout.write(self.style.SUCCESS("Local bootstrap completed."))

    def _ensure_admin_user(self, *, username: str, password: str):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if not user.is_staff:
            user.is_staff = True
        if not user.is_superuser:
            user.is_superuser = True
        if not user.is_active:
            user.is_active = True
        user.set_password(password)
        user.save()
        return user, created

    def _ensure_catalog(self) -> None:
        primary_material, _ = Material.objects.get_or_create(name="Повсть")

        product_names = [
            "Сумка клатч",
            "Сумка на плече",
            "Рюкзак",
            "Гаманець",
            "Косметичка",
        ]
        for name in product_names:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={"primary_material": primary_material},
            )
            if product.primary_material_id is None:
                product.primary_material = primary_material
                product.save(update_fields=["primary_material"])

        color_values = [
            ("Чорний", 1001),
            ("Білий", 1002),
            ("Синій", 1003),
            ("Червоний", 1004),
            ("Зелений", 1005),
        ]
        for name, code in color_values:
            MaterialColor.objects.get_or_create(
                material=primary_material,
                code=code,
                defaults={"name": name},
            )
