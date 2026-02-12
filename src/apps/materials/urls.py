from django.urls import path

from apps.materials.views import (
    MaterialColorCreateView,
    MaterialColorUpdateView,
    MaterialDetailView,
    MaterialListCreateView,
    material_archive,
    material_color_archive,
    material_unarchive,
    materials_archive,
)

urlpatterns = [
    path("materials/", MaterialListCreateView.as_view(), name="materials"),
    path("materials/archive/", materials_archive, name="materials_archive"),
    path("materials/<int:pk>/", MaterialDetailView.as_view(), name="material_detail"),
    path("materials/<int:pk>/archive/", material_archive, name="material_archive"),
    path("materials/<int:pk>/unarchive/", material_unarchive, name="material_unarchive"),
    # Material colors
    path(
        "materials/<int:pk>/colors/add/",
        MaterialColorCreateView.as_view(),
        name="material_color_add",
    ),
    path(
        "materials/<int:pk>/colors/<int:color_pk>/",
        MaterialColorUpdateView.as_view(),
        name="material_color_edit",
    ),
    path(
        "materials/<int:pk>/colors/<int:color_pk>/archive/",
        material_color_archive,
        name="material_color_archive",
    ),
]
