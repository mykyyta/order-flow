from django.urls import path

from apps.materials.views import (
    MaterialDetailUpdateView,
    MaterialListCreateView,
    materials_archive,
    material_archive,
    material_unarchive,
)

urlpatterns = [
    path("materials/", MaterialListCreateView.as_view(), name="materials"),
    path("materials/archive/", materials_archive, name="materials_archive"),
    path("materials/<int:pk>/", MaterialDetailUpdateView.as_view(), name="material_edit"),
    path("materials/<int:pk>/archive/", material_archive, name="material_archive"),
    path("materials/<int:pk>/unarchive/", material_unarchive, name="material_unarchive"),
]
