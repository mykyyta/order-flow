from django.urls import path

from apps.inventory.views import inventory_materials, inventory_products, inventory_wip

urlpatterns = [
    path("inventory/products/", inventory_products, name="inventory_products"),
    path("inventory/wip/", inventory_wip, name="inventory_wip"),
    path("inventory/materials/", inventory_materials, name="inventory_materials"),
]
