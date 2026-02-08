from django.urls import path

from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductModelListCreateView,
)

urlpatterns = [
    path("models/", ProductModelListCreateView.as_view(), name="product_models"),
    path("colors/", ColorListCreateView.as_view(), name="colors"),
    path("color/<int:pk>/", ColorDetailUpdateView.as_view(), name="color_edit"),
]
