from django.contrib import admin

from apps.procurement.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierOffer,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact_name", "phone", "email", "archived_at")
    search_fields = ("name", "contact_name", "email", "phone")


@admin.register(SupplierOffer)
class SupplierOfferAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "material", "material_color", "unit", "price_per_unit", "currency")
    list_filter = ("supplier", "material", "unit", "currency")
    search_fields = ("supplier__name", "material__name", "sku", "title")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "status", "expected_at", "created_at")
    list_filter = ("status", "supplier")
    search_fields = ("id", "supplier__name")


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "purchase_order",
        "material",
        "material_color",
        "quantity",
        "received_quantity",
        "unit",
        "unit_price",
    )
    list_filter = ("unit", "material")
    search_fields = ("purchase_order__id", "material__name")


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "purchase_order", "warehouse", "received_at")
    list_filter = ("supplier", "warehouse")
    search_fields = ("id", "supplier__name", "warehouse__name")


@admin.register(GoodsReceiptLine)
class GoodsReceiptLineAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt", "material", "material_color", "quantity", "unit", "unit_cost")
    list_filter = ("unit", "material")
    search_fields = ("receipt__id", "material__name")
