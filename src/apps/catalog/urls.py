from django.urls import path

from .views import (
    ProductDetailUpdateView,
    ProductListCreateView,
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
]
