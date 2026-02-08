from django.urls import path

from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductModelDetailUpdateView,
    ProductModelListCreateView,
    color_archive,
    color_unarchive,
    product_model_archive,
    product_model_unarchive,
)

urlpatterns = [
    path("models/", ProductModelListCreateView.as_view(), name="product_models"),
    path("models/<int:pk>/", ProductModelDetailUpdateView.as_view(), name="product_model_edit"),
    path("models/<int:pk>/archive/", product_model_archive, name="product_model_archive"),
    path("models/<int:pk>/unarchive/", product_model_unarchive, name="product_model_unarchive"),
    path("colors/", ColorListCreateView.as_view(), name="colors"),
    path("color/<int:pk>/", ColorDetailUpdateView.as_view(), name="color_edit"),
    path("color/<int:pk>/archive/", color_archive, name="color_archive"),
    path("color/<int:pk>/unarchive/", color_unarchive, name="color_unarchive"),
]
