from django.urls import path

from .views import (
    BundleComponentCreateView,
    BundleComponentUpdateView,
    ProductMaterialCreateView,
    ProductMaterialUpdateView,
    ProductDetailUpdateView,
    ProductListCreateView,
    bundle_component_delete,
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
        "products/<int:pk>/components/add/",
        BundleComponentCreateView.as_view(),
        name="bundle_component_add",
    ),
    path(
        "products/<int:pk>/components/<int:bc_pk>/",
        BundleComponentUpdateView.as_view(),
        name="bundle_component_edit",
    ),
    path(
        "products/<int:pk>/components/<int:bc_pk>/delete/",
        bundle_component_delete,
        name="bundle_component_delete",
    ),
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
