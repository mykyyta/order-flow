from decimal import Decimal

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_customer"

    def __str__(self) -> str:
        return self.name


class SalesOrder(models.Model):
    class Source(models.TextChoices):
        SITE = "site", "Сайт"
        ETSY = "is_etsy", "Etsy"
        WHOLESALE = "wholesale", "Опт"

    class Status(models.TextChoices):
        NEW = "new", "Нове"
        PROCESSING = "processing", "В обробці"
        PRODUCTION = "production", "На виробництві"
        READY = "ready", "Готове до відправки"
        SHIPPED = "shipped", "Відправлено"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Очікує"
        PARTIAL = "partial", "Частково"
        PAID = "paid", "Оплачено"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Готівка"
        CARD = "card", "Карта"
        TRANSFER = "transfer", "Переказ"
        OTHER = "other", "Інше"

    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    customer_info = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True,
    )
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"#{self.id} ({self.get_source_display()})"


class SalesOrderLine(models.Model):
    class ProductionMode(models.TextChoices):
        AUTO = "auto", "Авто"
        MANUAL = "manual_production", "Вручну"
        FORCE = "force_production", "Тільки виробництво"

    class ProductionStatus(models.TextChoices):
        PENDING = "pending", "Очікує"
        IN_PROGRESS = "in_progress", "У роботі"
        DONE = "done", "Готово"

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_lines",
    )
    bundle_preset = models.ForeignKey(
        "catalog.BundlePreset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_lines",
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
        return self.product.is_bundle

    def __str__(self) -> str:
        if self.variant:
            return f"{self.variant} x {self.quantity}"
        return f"{self.product.name} x {self.quantity}"


class SalesOrderLineComponentSelection(models.Model):
    order_line = models.ForeignKey(
        SalesOrderLine,
        on_delete=models.CASCADE,
        related_name="component_selections",
    )
    component = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_line_components",
    )

    class Meta:
        unique_together = ("order_line", "component")

    def __str__(self) -> str:
        if self.variant:
            return f"{self.component.name} -> {self.variant}"
        return f"{self.component.name}"
