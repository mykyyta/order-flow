from django.urls import path

from apps.materials.views import (
    MaterialColorCreateView,
    MaterialColorUpdateView,
    MaterialCreateView,
    MaterialDetailView,
    MaterialListView,
    material_archive,
    material_color_archive,
    material_color_unarchive,
    material_unarchive,
    material_colors_archive,
    materials_archive,
    purchases_list,
    suppliers_list,
)

urlpatterns = [
    path("materials/", MaterialListView.as_view(), name="materials"),
    path("materials/add/", MaterialCreateView.as_view(), name="material_add"),
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
    path(
        "materials/<int:pk>/colors/<int:color_pk>/unarchive/",
        material_color_unarchive,
        name="material_color_unarchive",
    ),
    path(
        "materials/<int:pk>/colors/archive/",
        material_colors_archive,
        name="material_colors_archive",
    ),
    # Suppliers
    path("suppliers/", suppliers_list, name="suppliers"),
    # Purchase orders
    path("purchases/", purchases_list, name="purchases"),
]
