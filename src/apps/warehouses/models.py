from django.db import models


class Warehouse(models.Model):
    class Kind(models.TextChoices):
        PRODUCTION = "production", "Виробництво"
        STORAGE = "storage", "Склад"
        RETAIL = "retail", "Роздріб"
        TRANSIT = "transit", "Транзит"

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.STORAGE)
    is_default_for_production = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_default_for_production"],
                condition=models.Q(is_default_for_production=True, is_active=True),
                name="warehouses_one_active_default_for_production",
            )
        ]
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
