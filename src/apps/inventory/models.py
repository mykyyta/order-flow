from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.variants import product_variant_matches_legacy_fields


class StockRecord(models.Model):
    product_model = models.ForeignKey(
        "catalog.ProductModel",
        on_delete=models.PROTECT,
        limit_choices_to={"is_bundle": False},
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_records_legacy",
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
        related_name="stock_records_primary_colors",
    )
    secondary_material_color = models.ForeignKey(
        "materials.MaterialColor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_records_secondary_colors",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "color"],
                name="inventory_stockrecord_product_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["product_model", "primary_material_color", "secondary_material_color"],
                name="inventory_stockrecord_product_material_color_uniq",
            ),
        ]
        verbose_name = "Залишок на складі"
        verbose_name_plural = "Залишки на складі"

    def __str__(self):
        if self.primary_material_color:
            color_name = self.primary_material_color.name
            if self.secondary_material_color:
                color_name = f"{color_name} / {self.secondary_material_color.name}"
        elif self.color:
            color_name = self.color.name
        else:
            color_name = "custom"
        return f"{self.product_model.name} ({color_name}): {self.quantity}"

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


class StockMovement(models.Model):
    class Reason(models.TextChoices):
        PRODUCTION_IN = "production_in", "Надходження з виробництва"
        ORDER_OUT = "order_out", "Відвантаження клієнту"
        ADJUSTMENT_IN = "adjustment_in", "Коригування +"
        ADJUSTMENT_OUT = "adjustment_out", "Коригування -"
        RETURN_IN = "return_in", "Повернення"

    stock_record = models.ForeignKey(
        StockRecord,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    quantity_change = models.IntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    related_production_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_customer_order_line = models.ForeignKey(
        "customer_orders.CustomerOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.stock_record}: {sign}{self.quantity_change}"
