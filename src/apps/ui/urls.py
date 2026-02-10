from django.urls import path

from apps.ui.views import palette_lab

urlpatterns = [
    path("palette/", palette_lab, name="palette_lab"),
]

