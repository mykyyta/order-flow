from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.variants import product_variant_matches_legacy_fields


class CustomerOrder(models.Model):
    class Source(models.TextChoices):
        SITE = "site", "Сайт"
        ETSY = "etsy", "Etsy"
        WHOLESALE = "wholesale", "Опт"

    class Status(models.TextChoices):
        NEW = "new", "Нове"
        PROCESSING = "processing", "В обробці"
        PRODUCTION = "production", "На виробництві"
        READY = "ready", "Готове до відправки"
        SHIPPED = "shipped", "Відправлено"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    customer_info = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"#{self.id} ({self.get_source_display()})"


class CustomerOrderLine(models.Model):
    class ProductionMode(models.TextChoices):
        AUTO = "auto", "Авто"
        MANUAL = "manual_production", "Вручну"
        FORCE = "force_production", "Тільки виробництво"

    class ProductionStatus(models.TextChoices):
        PENDING = "pending", "Очікує"
        IN_PROGRESS = "in_progress", "У роботі"
        DONE = "done", "Готово"

    customer_order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product_model = models.ForeignKey(
        "catalog.ProductModel",
        on_delete=models.PROTECT,
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_lines_legacy",
    )
    color = models.ForeignKey(
        "catalog.Color",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    primary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_order_line_primary_colors",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_order_line_secondary_colors",
    )
    bundle_preset = models.ForeignKey(
        "catalog.BundlePreset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_lines",
    )
    quantity = models.PositiveIntegerField(default=1)
    production_mode = models.CharField(
        max_length=24,
        choices=ProductionMode.choices,
        default=ProductionMode.AUTO,
    )
    production_status = models.CharField(
        max_length=20,
        choices=ProductionStatus.choices,
        default=ProductionStatus.PENDING,
    )

    class Meta:
        ordering = ("id",)

    @property
    def is_bundle(self) -> bool:
        return self.product_model.is_bundle

    def __str__(self):
        if self.primary_material_color:
            color_str = self.primary_material_color.name
            if self.secondary_material_color:
                color_str = f"{color_str} / {self.secondary_material_color.name}"
        elif self.color:
            color_str = self.color.name
        else:
            color_str = "custom"
        return f"{self.product_model.name} ({color_str}) x {self.quantity}"

    def _validate_product_variant_consistency(self) -> None:
        if self.product_variant_id is None:
            return

        if not product_variant_matches_legacy_fields(
            product_variant=self.product_variant,
            product_model_id=self.product_model_id,
            color_id=self.color_id,
            primary_material_color_id=self.primary_material_color_id,
            secondary_material_color_id=self.secondary_material_color_id,
        ):
            raise ValidationError(
                {"product_variant": "Product variant must match product/color/material colors fields."}
            )

    def save(self, *args, **kwargs) -> None:
        self._validate_product_variant_consistency()
        super().save(*args, **kwargs)


class CustomerOrderLineComponent(models.Model):
    order_line = models.ForeignKey(
        CustomerOrderLine,
        on_delete=models.CASCADE,
        related_name="component_colors",
    )
    component = models.ForeignKey(
        "catalog.ProductModel",
        on_delete=models.PROTECT,
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_line_components_legacy",
    )
    color = models.ForeignKey(
        "catalog.Color",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    primary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_order_component_primary_colors",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_order_component_secondary_colors",
    )

    class Meta:
        unique_together = ("order_line", "component")

    def __str__(self):
        if self.primary_material_color:
            return f"{self.component.name} -> {self.primary_material_color.name}"
        if self.color:
            return f"{self.component.name} -> {self.color.name}"
        return f"{self.component.name} -> custom"

    def _validate_product_variant_consistency(self) -> None:
        if self.product_variant_id is None:
            return

        if not product_variant_matches_legacy_fields(
            product_variant=self.product_variant,
            product_model_id=self.component_id,
            color_id=self.color_id,
            primary_material_color_id=self.primary_material_color_id,
            secondary_material_color_id=self.secondary_material_color_id,
        ):
            raise ValidationError(
                {"product_variant": "Product variant must match component/color/material colors fields."}
            )

    def save(self, *args, **kwargs) -> None:
        self._validate_product_variant_consistency()
        super().save(*args, **kwargs)
