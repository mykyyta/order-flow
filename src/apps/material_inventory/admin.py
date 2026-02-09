from django.contrib import admin

from apps.material_inventory.models import (
    MaterialStockMovement,
    MaterialStockRecord,
    MaterialStockTransfer,
    MaterialStockTransferLine,
)


@admin.register(MaterialStockRecord)
class MaterialStockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "warehouse", "material", "material_color", "quantity", "unit")
    list_filter = ("warehouse", "unit", "material")
    search_fields = ("material__name", "material_color__name", "warehouse__name")


@admin.register(MaterialStockMovement)
class MaterialStockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "stock_record", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("stock_record__material__name",)


@admin.register(MaterialStockTransfer)
class MaterialStockTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "from_warehouse", "to_warehouse", "status", "created_at", "completed_at")
    list_filter = ("status", "from_warehouse", "to_warehouse")
    search_fields = ("id", "from_warehouse__name", "to_warehouse__name")


@admin.register(MaterialStockTransferLine)
class MaterialStockTransferLineAdmin(admin.ModelAdmin):
    list_display = ("id", "transfer", "material", "material_color", "quantity", "unit")
    list_filter = ("unit", "material")
    search_fields = ("transfer__id", "material__name", "material_color__name")
