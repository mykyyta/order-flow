from django.db import models
from django.utils import timezone


class ProductModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    is_bundle = models.BooleanField(default=False)
    primary_material = models.ForeignKey(
        "materials.Material",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="primary_products",
    )
    secondary_material = models.ForeignKey(
        "materials.Material",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="secondary_products",
    )
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class Color(models.Model):
    AVAILABILITY_CHOICES = [
        ("in_stock", "В наявності"),
        ("low_stock", "Закінчується"),
        ("out_of_stock", "Немає"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    code = models.IntegerField(unique=True)
    availability_status = models.CharField(
        max_length=20, choices=AVAILABILITY_CHOICES, default="in_stock"
    )
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class BundleComponent(models.Model):
    bundle = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="components",
        limit_choices_to={"is_bundle": True},
    )
    component = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="part_of_bundles",
        limit_choices_to={"is_bundle": False},
    )
    is_primary = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("bundle", "component")
        ordering = ("-is_primary", "id")

    def __str__(self):
        return f"{self.bundle.name} -> {self.component.name}"


class BundleColorMapping(models.Model):
    bundle = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="color_mappings",
        limit_choices_to={"is_bundle": True},
    )
    bundle_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name="as_bundle_color",
    )
    component = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="bundle_color_components",
        limit_choices_to={"is_bundle": False},
    )
    component_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name="as_component_color",
    )

    class Meta:
        unique_together = ("bundle", "bundle_color", "component")

    def __str__(self):
        return (
            f"{self.bundle.name}[{self.bundle_color.name}]"
            f": {self.component.name}={self.component_color.name}"
        )


class BundlePreset(models.Model):
    bundle = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="presets",
        limit_choices_to={"is_bundle": True},
    )
    name = models.CharField(max_length=255)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bundle", "name")
        ordering = ("bundle_id", "name")

    def __str__(self):
        return f"{self.bundle.name}: {self.name}"


class BundlePresetComponent(models.Model):
    preset = models.ForeignKey(
        BundlePreset,
        on_delete=models.CASCADE,
        related_name="components",
    )
    component = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="bundle_presets",
        limit_choices_to={"is_bundle": False},
    )
    primary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        related_name="bundle_preset_primary_components",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bundle_preset_secondary_components",
    )

    class Meta:
        unique_together = ("preset", "component")
        ordering = ("preset_id", "component_id")

    def __str__(self):
        return f"{self.preset}: {self.component.name}"
