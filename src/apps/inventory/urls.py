from django.urls import path

from apps.inventory.views import (
    inventory_material_stock_detail,
    inventory_materials,
    inventory_materials_add,
    inventory_materials_remove,
    inventory_product_stock_detail,
    inventory_products,
    inventory_products_add,
    inventory_products_remove,
    inventory_wip,
)

urlpatterns = [
    path("inventory/products/", inventory_products, name="inventory_products"),
    path(
        "inventory/products/stock/<int:pk>/",
        inventory_product_stock_detail,
        name="inventory_product_stock_detail",
    ),
    path("inventory/products/add/", inventory_products_add, name="inventory_products_add"),
    path("inventory/products/remove/", inventory_products_remove, name="inventory_products_remove"),
    path("inventory/wip/", inventory_wip, name="inventory_wip"),
    path("inventory/materials/", inventory_materials, name="inventory_materials"),
    path(
        "inventory/materials/stock/<int:pk>/",
        inventory_material_stock_detail,
        name="inventory_material_stock_detail",
    ),
    path("inventory/materials/add/", inventory_materials_add, name="inventory_materials_add"),
    path("inventory/materials/remove/", inventory_materials_remove, name="inventory_materials_remove"),
]
