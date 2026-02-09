from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Material(models.Model):
    name = models.CharField(max_length=255, unique=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class MaterialColor(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="colors",
    )
    name = models.CharField(max_length=255)
    code = models.IntegerField()
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            ("material", "name"),
            ("material", "code"),
        )
        ordering = ("material__name", "name")

    def __str__(self) -> str:
        return f"{self.material.name}: {self.name}"


class ProductMaterial(models.Model):
    class Unit(models.TextChoices):
        PIECE = "pcs", "шт"
        METER = "m", "м"
        SQUARE_METER = "m2", "м²"
        GRAM = "g", "г"
        MILLILITER = "ml", "мл"

    product_model = models.ForeignKey(
        "catalog.ProductModel",
        on_delete=models.CASCADE,
        related_name="material_norms",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="product_norms",
    )
    quantity_per_unit = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=8, choices=Unit.choices)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("product_model", "material"),)
        ordering = ("product_model_id", "material__name")

    def __str__(self) -> str:
        quantity = Decimal(str(self.quantity_per_unit))
        return (
            f"{self.product_model.name}: {self.material.name}"
            f" {quantity:.2f} {self.unit}"
        )


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class SupplierMaterialOffer(models.Model):
    class Currency(models.TextChoices):
        UAH = "UAH", "UAH"
        USD = "USD", "USD"
        EUR = "EUR", "EUR"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    material_color = models.ForeignKey(
        MaterialColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_offers",
    )
    title = models.CharField(max_length=255, blank=True)
    sku = models.CharField(max_length=128, blank=True)
    unit = models.CharField(max_length=8, choices=ProductMaterial.Unit.choices)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.UAH)
    min_order_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("supplier__name", "material__name", "-created_at")

    def clean(self) -> None:
        if self.material_color and self.material_color.material_id != self.material_id:
            raise ValidationError("Material color must belong to selected material.")

    def __str__(self) -> str:
        color_name = self.material_color.name if self.material_color else "-"
        return f"{self.supplier.name}: {self.material.name} ({color_name})"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        SENT = "sent", "Відправлено"
        PARTIALLY_RECEIVED = "partially_received", "Частково отримано"
        RECEIVED = "received", "Отримано"
        CANCELLED = "cancelled", "Скасовано"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    expected_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"PO #{self.id} ({self.supplier.name})"


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )
    material_color = models.ForeignKey(
        MaterialColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_order_lines",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    unit = models.CharField(max_length=8, choices=ProductMaterial.Unit.choices)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("purchase_order_id", "id")

    @property
    def remaining_quantity(self) -> Decimal:
        remaining = self.quantity - self.received_quantity
        return max(remaining, Decimal("0.000"))

    def clean(self) -> None:
        if self.material_color and self.material_color.material_id != self.material_id:
            raise ValidationError("Material color must belong to selected material.")

    def __str__(self) -> str:
        return f"PO #{self.purchase_order_id}: {self.material.name} {self.quantity} {self.unit}"


class MaterialStockRecord(models.Model):
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="material_stock_records_legacy",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="stock_records",
    )
    material_color = models.ForeignKey(
        MaterialColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_records",
    )
    unit = models.CharField(max_length=8, choices=ProductMaterial.Unit.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["material", "unit"],
                condition=models.Q(material_color__isnull=True, warehouse__isnull=True),
                name="materials_stock_material_unit_null_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["material", "material_color", "unit"],
                condition=models.Q(material_color__isnull=False, warehouse__isnull=True),
                name="materials_stock_material_color_unit_uniq",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "material", "unit"],
                condition=models.Q(material_color__isnull=True, warehouse__isnull=False),
                name="materials_stock_warehouse_material_unit_null_color_uniq",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "material", "material_color", "unit"],
                condition=models.Q(material_color__isnull=False, warehouse__isnull=False),
                name="materials_stock_warehouse_material_color_unit_uniq",
            ),
        ]
        ordering = ("material__name",)

    def clean(self) -> None:
        if self.material_color and self.material_color.material_id != self.material_id:
            raise ValidationError("Material color must belong to selected material.")

    def __str__(self) -> str:
        color_name = self.material_color.name if self.material_color else "-"
        return f"{self.material.name} ({color_name}) {self.quantity} {self.unit}"


class GoodsReceipt(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="goods_receipts",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goods_receipts",
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="goods_receipts_legacy",
    )
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_goods_receipts",
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self) -> str:
        return f"Receipt #{self.id} ({self.supplier.name})"


class GoodsReceiptLine(models.Model):
    receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_lines",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="goods_receipt_lines",
    )
    material_color = models.ForeignKey(
        MaterialColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="goods_receipt_lines",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=8, choices=ProductMaterial.Unit.choices)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("receipt_id", "id")

    def clean(self) -> None:
        if self.material_color and self.material_color.material_id != self.material_id:
            raise ValidationError("Material color must belong to selected material.")

    def __str__(self) -> str:
        return f"Receipt #{self.receipt_id}: {self.material.name} {self.quantity} {self.unit}"


class MaterialMovement(models.Model):
    class Reason(models.TextChoices):
        PURCHASE_IN = "purchase_in", "Надходження від постачальника"
        PRODUCTION_OUT = "production_out", "Списання у виробництво"
        TRANSFER_IN = "transfer_in", "Надходження зі складу"
        TRANSFER_OUT = "transfer_out", "Переміщення на склад"
        ADJUSTMENT_IN = "adjustment_in", "Коригування +"
        ADJUSTMENT_OUT = "adjustment_out", "Коригування -"
        RETURN_IN = "return_in", "Повернення"

    stock_record = models.ForeignKey(
        MaterialStockRecord,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    quantity_change = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=24, choices=Reason.choices)
    related_purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_movements",
    )
    related_receipt_line = models.ForeignKey(
        GoodsReceiptLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_movements",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.stock_record}: {sign}{self.quantity_change}"


class MaterialStockTransfer(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_TRANSIT = "in_transit", "В дорозі"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    from_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="material_stock_transfers_out",
    )
    to_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.PROTECT,
        related_name="material_stock_transfers_in",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        "orders.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_material_stock_transfers",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_warehouse=models.F("to_warehouse")),
                name="materials_materialstocktransfer_from_to_different",
            ),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.from_warehouse.code} -> {self.to_warehouse.code} ({self.status})"


class MaterialStockTransferLine(models.Model):
    transfer = models.ForeignKey(
        MaterialStockTransfer,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="stock_transfer_lines",
    )
    material_color = models.ForeignKey(
        MaterialColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_transfer_lines",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=8, choices=ProductMaterial.Unit.choices)

    class Meta:
        ordering = ("transfer_id", "id")

    def clean(self) -> None:
        if self.material_color and self.material_color.material_id != self.material_id:
            raise ValidationError("Material color must belong to selected material.")

    def __str__(self) -> str:
        return f"{self.transfer_id}: {self.material.name} {self.quantity} {self.unit}"
