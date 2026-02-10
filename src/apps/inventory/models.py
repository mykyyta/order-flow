from django.db import models

from config import settings


class ProductStockQuerySet(models.QuerySet):
    def for_warehouse(self, warehouse_id: int):
        return self.filter(warehouse_id=warehouse_id)

    def for_variant(self, variant_id: int):
        return self.filter(variant_id=variant_id)

    def with_positive_quantity(self):
        return self.filter(quantity__gt=0)


ProductStockManager = models.Manager.from_queryset(ProductStockQuerySet)


class ProductStock(models.Model):
    objects = ProductStockManager()

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="product_stocks",
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        related_name="product_stocks",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "variant"],
                name="inventory_stockrecord_warehouse_variant_uniq",
            ),
        ]
        verbose_name = "Залишок на складі"
        verbose_name_plural = "Залишки на складі"

    def __str__(self):
        return f"{self.variant}: {self.quantity}"


class ProductStockMovement(models.Model):
    class Reason(models.TextChoices):
        PRODUCTION_IN = "production_in", "Надходження з виробництва"
        ORDER_OUT = "order_out", "Відвантаження клієнту"
        TRANSFER_IN = "transfer_in", "Надходження зі складу"
        TRANSFER_OUT = "transfer_out", "Переміщення на склад"
        ADJUSTMENT_IN = "adjustment_in", "Коригування +"
        ADJUSTMENT_OUT = "adjustment_out", "Коригування -"
        RETURN_IN = "return_in", "Повернення"

    stock_record = models.ForeignKey(
        ProductStock,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    quantity_change = models.IntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    related_production_order = models.ForeignKey(
        "production.ProductionOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sales_order_line = models.ForeignKey(
        "sales.SalesOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_transfer = models.ForeignKey(
        "inventory.ProductStockTransfer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.stock_record}: {sign}{self.quantity_change}"


class WIPStockRecord(models.Model):
    class QuerySet(models.QuerySet):
        def for_warehouse(self, warehouse_id: int):
            return self.filter(warehouse_id=warehouse_id)

        def for_variant(self, variant_id: int):
            return self.filter(variant_id=variant_id)

        def with_positive_quantity(self):
            return self.filter(quantity__gt=0)

    objects = models.Manager.from_queryset(QuerySet)()

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="wip_stocks",
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        related_name="wip_stocks",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "variant"],
                name="inventory_wipstockrecord_warehouse_variant_uniq",
            ),
        ]
        verbose_name = "WIP залишок"
        verbose_name_plural = "WIP залишки"

    def __str__(self) -> str:
        return f"{self.warehouse.code}: {self.variant} ({self.quantity})"


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
        "production.ProductionOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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


class ProductStockTransfer(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_TRANSIT = "in_transit", "В дорозі"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    from_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="product_stock_transfers_out",
    )
    to_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="product_stock_transfers_in",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_product_stock_transfers",
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


class ProductStockTransferLine(models.Model):
    transfer = models.ForeignKey(
        ProductStockTransfer,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        related_name="product_stock_transfer_lines",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "variant"],
                name="inventory_finishedstocktransferline_transfer_variant_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transfer_id}: {self.variant_id} x {self.quantity}"
