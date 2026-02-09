from django.urls import path

from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductModelDetailUpdateView,
    ProductModelListCreateView,
    colors_archive,
    color_archive,
    color_unarchive,
    product_models_archive,
    product_model_archive,
    product_model_unarchive,
)

urlpatterns = [
    path("models/", ProductModelListCreateView.as_view(), name="product_models"),
    path("models/archive/", product_models_archive, name="product_models_archive"),
    path("models/<int:pk>/", ProductModelDetailUpdateView.as_view(), name="product_model_edit"),
    path("models/<int:pk>/archive/", product_model_archive, name="product_model_archive"),
    path("models/<int:pk>/unarchive/", product_model_unarchive, name="product_model_unarchive"),
    path("colors/", ColorListCreateView.as_view(), name="colors"),
    path("colors/archive/", colors_archive, name="colors_archive"),
    path("colors/<int:pk>/", ColorDetailUpdateView.as_view(), name="color_edit"),
    path("colors/<int:pk>/archive/", color_archive, name="color_archive"),
    path("colors/<int:pk>/unarchive/", color_unarchive, name="color_unarchive"),
]
