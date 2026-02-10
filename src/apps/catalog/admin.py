from django.contrib import admin
from .models import Color, Product


@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "archived_at")


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "status", "archived_at")
