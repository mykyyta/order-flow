from django.urls import path

from .views import (
    ProductMaterialCreateView,
    ProductMaterialUpdateView,
    ProductDetailUpdateView,
    ProductListCreateView,
    products_archive,
    product_archive,
    product_unarchive,
    product_material_delete,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="products"),
    path("products/archive/", products_archive, name="products_archive"),
    path("products/<int:pk>/", ProductDetailUpdateView.as_view(), name="product_edit"),
    path(
        "products/<int:pk>/materials/add/",
        ProductMaterialCreateView.as_view(),
        name="product_material_add",
    ),
    path(
        "products/<int:pk>/materials/<int:pm_pk>/",
        ProductMaterialUpdateView.as_view(),
        name="product_material_edit",
    ),
    path(
        "products/<int:pk>/materials/<int:pm_pk>/delete/",
        product_material_delete,
        name="product_material_delete",
    ),
    path("products/<int:pk>/archive/", product_archive, name="product_archive"),
    path("products/<int:pk>/unarchive/", product_unarchive, name="product_unarchive"),
]
