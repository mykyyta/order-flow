from django.contrib import admin

from apps.inventory.models import (
    FinishedStockTransfer,
    FinishedStockTransferLine,
    StockMovement,
    StockRecord,
    WIPStockMovement,
    WIPStockRecord,
)


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "product_model", "product_variant", "quantity")
    list_filter = ("warehouse", "product_model")
    search_fields = ("product_model__name", "product_variant__sku")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__product_model__name",)


@admin.register(WIPStockRecord)
class WIPStockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "product_variant", "quantity")
    list_filter = ("warehouse",)
    search_fields = ("product_variant__product__name",)


@admin.register(WIPStockMovement)
class WIPStockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__product_variant__product__name",)


@admin.register(FinishedStockTransfer)
class FinishedStockTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "from_warehouse", "to_warehouse", "status", "created_at", "completed_at")
    list_filter = ("status", "from_warehouse", "to_warehouse")
    search_fields = ("id", "from_warehouse__name", "to_warehouse__name")


@admin.register(FinishedStockTransferLine)
class FinishedStockTransferLineAdmin(admin.ModelAdmin):
    list_display = ("id", "transfer", "product_variant", "quantity")
    search_fields = ("transfer__id", "product_variant__product__name")
