from django.contrib import admin

from apps.materials.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    Material,
    MaterialColor,
    MaterialMovement,
    MaterialStockRecord,
    ProductMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierMaterialOffer,
)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "archived_at")


@admin.register(MaterialColor)
class MaterialColorAdmin(admin.ModelAdmin):
    list_display = ("id", "material", "name", "code", "archived_at")
    list_filter = ("material",)
    search_fields = ("name", "material__name")


@admin.register(ProductMaterial)
class ProductMaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "product_model", "material", "quantity_per_unit", "unit")
    list_filter = ("unit", "material")
    search_fields = ("product_model__name", "material__name")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact_name", "phone", "email", "archived_at")
    search_fields = ("name", "contact_name", "email", "phone")


@admin.register(SupplierMaterialOffer)
class SupplierMaterialOfferAdmin(admin.ModelAdmin):
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


@admin.register(MaterialStockRecord)
class MaterialStockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "material", "material_color", "quantity", "unit")
    list_filter = ("unit", "material")
    search_fields = ("material__name", "material_color__name")


@admin.register(MaterialMovement)
class MaterialMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__material__name",)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "purchase_order", "received_at")
    list_filter = ("supplier",)
    search_fields = ("id", "supplier__name")


@admin.register(GoodsReceiptLine)
class GoodsReceiptLineAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt", "material", "material_color", "quantity", "unit", "unit_cost")
    list_filter = ("unit", "material")
    search_fields = ("receipt__id", "material__name")
