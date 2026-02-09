from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.variants import product_variant_matches_legacy_fields


class StockRecord(models.Model):
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finished_stock_records_legacy",
    )
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
                condition=models.Q(warehouse__isnull=True),
                name="inventory_stockrecord_product_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["product_model", "primary_material_color", "secondary_material_color"],
                condition=models.Q(warehouse__isnull=True),
                name="inventory_stockrecord_product_material_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "product_model", "color"],
                condition=models.Q(warehouse__isnull=False),
                name="inventory_stockrecord_warehouse_product_color_uniq",
            ),
            models.UniqueConstraint(
                fields=[
                    "warehouse",
                    "product_model",
                    "primary_material_color",
                    "secondary_material_color",
                ],
                condition=models.Q(warehouse__isnull=False),
                name="inventory_stockrecord_warehouse_product_material_color_uniq",
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
        TRANSFER_IN = "transfer_in", "Надходження зі складу"
        TRANSFER_OUT = "transfer_out", "Переміщення на склад"
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


FinishedStockRecord = StockRecord
FinishedStockMovement = StockMovement


class WIPStockRecord(models.Model):
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="wip_stock_records",
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="wip_stock_records",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "product_variant"],
                name="inventory_wipstockrecord_warehouse_variant_uniq",
            ),
        ]
        verbose_name = "WIP залишок"
        verbose_name_plural = "WIP залишки"

    def __str__(self) -> str:
        return f"{self.warehouse.code}: {self.product_variant} ({self.quantity})"


class WIPStockMovement(models.Model):
    class Reason(models.TextChoices):
        CUTTING_IN = "cutting_in", "Порізка в WIP"
        FINISHING_OUT = "finishing_out", "Вибуття з WIP на доробку"
        SCRAP_OUT = "scrap_out", "Списання браку з WIP"
        ADJUSTMENT_IN = "adjustment_in", "Коригування +"
        ADJUSTMENT_OUT = "adjustment_out", "Коригування -"

    stock_record = models.ForeignKey(
        WIPStockRecord,
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
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.stock_record}: {sign}{self.quantity_change}"


class FinishedStockTransfer(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_TRANSIT = "in_transit", "В дорозі"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    from_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="finished_stock_transfers_out",
    )
    to_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="finished_stock_transfers_in",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finished_stock_transfers",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_warehouse=models.F("to_warehouse")),
                name="inventory_finishedstocktransfer_from_to_different",
            ),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.from_warehouse.code} -> {self.to_warehouse.code} ({self.status})"


class FinishedStockTransferLine(models.Model):
    transfer = models.ForeignKey(
        FinishedStockTransfer,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="finished_stock_transfer_lines",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "product_variant"],
                name="inventory_finishedstocktransferline_transfer_variant_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transfer_id}: {self.product_variant_id} x {self.quantity}"
