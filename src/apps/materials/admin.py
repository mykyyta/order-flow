from django.contrib import admin

from apps.materials.models import (
    Material,
    MaterialColor,
    ProductMaterial,
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

