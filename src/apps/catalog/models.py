from django.db import models
from django.utils import timezone

from apps.materials.models import MaterialUnit


class Product(models.Model):
    class Kind(models.TextChoices):
        STANDARD = "standard", "Звичайний"
        COMPONENT = "component", "Компонент"
        BUNDLE = "bundle", "Бандл"

    name = models.CharField(max_length=255, unique=True)
    section = models.CharField(max_length=255, blank=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="UAH")
    # Роздрібна ціна в Україні (грн). Інші ціни — окремими полями пізніше.
    price_retail_uah = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.STANDARD,
        db_index=True,
    )
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

    @property
    def is_bundle(self) -> bool:
        return self.kind == self.Kind.BUNDLE

    def __str__(self):
        return f"{self.name}"


class ProductMaterial(models.Model):
    class Role(models.TextChoices):
        PRIMARY = "primary", "Основний"
        SECONDARY = "secondary", "Другорядний"
        OTHER = "other", "Інший"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    material = models.ForeignKey(
        "materials.Material",
        on_delete=models.PROTECT,
        related_name="product_material_links",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.OTHER)
    notes = models.CharField(max_length=255, blank=True)
    quantity_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    unit = models.CharField(
        max_length=8,
        choices=MaterialUnit.choices,
        null=True,
        blank=True,
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "material"],
                name="catalog_productmaterial_product_material_uniq",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(role="primary"),
                name="catalog_productmaterial_primary_uniq_per_product",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(role="secondary"),
                name="catalog_productmaterial_secondary_uniq_per_product",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(quantity_per_unit__isnull=True) & models.Q(unit__isnull=True))
                    | (models.Q(quantity_per_unit__isnull=False) & models.Q(unit__isnull=False))
                ),
                name="catalog_productmaterial_norm_quantity_unit_nullability",
            ),
        ]
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return f"{self.product.name}: {self.material.name} ({self.get_role_display()})"


class Color(models.Model):
    AVAILABILITY_CHOICES = [
        ("in_stock", "В наявності"),
        ("low_stock", "Закінчується"),
        ("out_of_stock", "Немає"),
    ]

    name = models.CharField(max_length=255, unique=True)
    code = models.IntegerField(unique=True)
    status = models.CharField(
        max_length=20, choices=AVAILABILITY_CHOICES, default="in_stock"
    )
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"


class Variant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="variants",
    )
    primary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="variants_primary",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="variants_secondary",
    )
    sku = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    legacy_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color"],
                condition=(
                    models.Q(color__isnull=False)
                    & models.Q(primary_material_color__isnull=True)
                    & models.Q(secondary_material_color__isnull=True)
                ),
                name="catalog_productvariant_product_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["product", "primary_material_color"],
                condition=(
                    models.Q(color__isnull=True)
                    & models.Q(primary_material_color__isnull=False)
                    & models.Q(secondary_material_color__isnull=True)
                ),
                name="catalog_productvariant_primary_only_uniq",
            ),
            models.UniqueConstraint(
                fields=["product", "primary_material_color", "secondary_material_color"],
                condition=(
                    models.Q(color__isnull=True)
                    & models.Q(primary_material_color__isnull=False)
                    & models.Q(secondary_material_color__isnull=False)
                ),
                name="catalog_productvariant_primary_secondary_uniq",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=(
                    models.Q(color__isnull=True)
                    & models.Q(primary_material_color__isnull=True)
                    & models.Q(secondary_material_color__isnull=True)
                ),
                name="catalog_productvariant_uncolored_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(color__isnull=True)
                    | models.Q(primary_material_color__isnull=True)
                ),
                name="catalog_productvariant_color_primary_exclusive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(secondary_material_color__isnull=True)
                    | models.Q(primary_material_color__isnull=False)
                ),
                name="catalog_productvariant_secondary_requires_primary",
            ),
        ]
        ordering = ("product_id", "id")

    def __str__(self) -> str:
        if self.primary_material_color:
            primary_name = self.primary_material_color.name
            if self.secondary_material_color:
                return f"{self.product.name} ({primary_name} / {self.secondary_material_color.name})"
            return f"{self.product.name} ({primary_name})"
        return f"{self.product.name} (custom)"

    def display_color_label(self) -> str:
        if self.primary_material_color:
            if self.secondary_material_color:
                return f"{self.primary_material_color.name} / {self.secondary_material_color.name}"
            return self.primary_material_color.name
        return "-"


class BundleComponent(models.Model):
    bundle = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="components",
        limit_choices_to={"kind": Product.Kind.BUNDLE},
    )
    component = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="part_of_bundles",
        limit_choices_to=models.Q(kind=Product.Kind.STANDARD) | models.Q(kind=Product.Kind.COMPONENT),
    )
    is_primary = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)
    group = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("bundle", "component")
        ordering = ("-is_primary", "id")

    def __str__(self):
        return f"{self.bundle.name} -> {self.component.name}"


class BundleColorMapping(models.Model):
    bundle = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="color_mappings",
        limit_choices_to={"kind": Product.Kind.BUNDLE},
    )
    bundle_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name="as_bundle_color",
    )
    component = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="bundle_color_components",
        limit_choices_to=models.Q(kind=Product.Kind.STANDARD) | models.Q(kind=Product.Kind.COMPONENT),
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
        Product,
        on_delete=models.CASCADE,
        related_name="presets",
        limit_choices_to={"kind": Product.Kind.BUNDLE},
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
        Product,
        on_delete=models.CASCADE,
        related_name="bundle_presets",
        limit_choices_to=models.Q(kind=Product.Kind.STANDARD) | models.Q(kind=Product.Kind.COMPONENT),
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
