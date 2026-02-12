from django.contrib import admin

from apps.inventory.models import (
    ProductStockTransfer,
    ProductStockTransferLine,
    ProductStockMovement,
    ProductStock,
    WIPStockMovement,
    WIPStockRecord,
)


@admin.register(ProductStock)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "variant", "quantity")
    list_filter = ("warehouse",)
    search_fields = ("variant__product__name", "variant__sku")


@admin.register(ProductStockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__variant__product__name",)


@admin.register(WIPStockRecord)
class WIPStockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "variant", "quantity")
    list_filter = ("warehouse",)
    search_fields = ("variant__product__name",)


@admin.register(WIPStockMovement)
class WIPStockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__variant__product__name",)


@admin.register(ProductStockTransfer)
class FinishedStockTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "from_warehouse", "to_warehouse", "status", "created_at", "completed_at")
    list_filter = ("status", "from_warehouse", "to_warehouse")
    search_fields = ("id", "from_warehouse__name", "to_warehouse__name")


@admin.register(ProductStockTransferLine)
class FinishedStockTransferLineAdmin(admin.ModelAdmin):
    list_display = ("id", "transfer", "variant", "quantity")
    search_fields = ("transfer__id", "variant__product__name")
