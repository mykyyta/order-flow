from django.db import models
from config import settings


class StockRecord(models.Model):
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="finished_stock_records_legacy",
    )
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_records_legacy",
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "product_variant"],
                name="inventory_stockrecord_warehouse_variant_uniq",
            ),
        ]
        verbose_name = "Залишок на складі"
        verbose_name_plural = "Залишки на складі"

    def __str__(self):
        return f"{self.product_variant}: {self.quantity}"


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
        "production.ProductionOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_customer_order_line = models.ForeignKey(
        "sales.SalesOrderLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_transfer = models.ForeignKey(
        "inventory.FinishedStockTransfer",
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
        settings.AUTH_USER_MODEL,
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
