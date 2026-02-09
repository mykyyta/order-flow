from django.contrib import admin

from apps.warehouses.models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "is_default_for_production", "is_active")
    list_filter = ("kind", "is_default_for_production", "is_active")
    search_fields = ("name", "code")
