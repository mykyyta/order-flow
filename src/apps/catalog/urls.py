from django.urls import path

from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductDetailUpdateView,
    ProductListCreateView,
    colors_archive,
    color_archive,
    color_unarchive,
    products_archive,
    product_archive,
    product_unarchive,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="products"),
    path("products/archive/", products_archive, name="products_archive"),
    path("products/<int:pk>/", ProductDetailUpdateView.as_view(), name="product_edit"),
    path("products/<int:pk>/archive/", product_archive, name="product_archive"),
    path("products/<int:pk>/unarchive/", product_unarchive, name="product_unarchive"),
    path("colors/", ColorListCreateView.as_view(), name="colors"),
    path("colors/archive/", colors_archive, name="colors_archive"),
    path("colors/<int:pk>/", ColorDetailUpdateView.as_view(), name="color_edit"),
    path("colors/<int:pk>/archive/", color_archive, name="color_archive"),
    path("colors/<int:pk>/unarchive/", color_unarchive, name="color_unarchive"),
]
