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
    purchase_add,
    purchase_detail,
    purchase_line_add,
    purchase_line_receive,
    purchase_request_add,
    purchase_request_detail,
    purchase_request_line_add,
    purchase_request_line_set_status,
    purchase_request_line_order,
    purchase_request_set_status,
    purchase_requests_list,
    purchase_set_status,
    purchases_list,
    suppliers_list,
    purchase_pick_request_line_for_order,
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
    path("purchases/add/", purchase_add, name="purchase_add"),
    path("purchases/<int:pk>/", purchase_detail, name="purchase_detail"),
    path("purchases/<int:pk>/status/", purchase_set_status, name="purchase_set_status"),
    path("purchases/<int:pk>/lines/add/", purchase_line_add, name="purchase_line_add"),
    path(
        "purchases/<int:pk>/from-request/",
        purchase_pick_request_line_for_order,
        name="purchase_pick_request_line_for_order",
    ),
    path(
        "purchases/<int:pk>/lines/<int:line_pk>/receive/",
        purchase_line_receive,
        name="purchase_line_receive",
    ),
    # Purchase requests
    path("purchase-requests/", purchase_requests_list, name="purchase_requests"),
    path("purchase-requests/add/", purchase_request_add, name="purchase_request_add"),
    path(
        "purchase-requests/<int:pk>/",
        purchase_request_detail,
        name="purchase_request_detail",
    ),
    path(
        "purchase-requests/<int:pk>/status/",
        purchase_request_set_status,
        name="purchase_request_set_status",
    ),
    path(
        "purchase-requests/<int:pk>/lines/add/",
        purchase_request_line_add,
        name="purchase_request_line_add",
    ),
    path(
        "purchase-requests/lines/<int:line_pk>/order/",
        purchase_request_line_order,
        name="purchase_request_line_order",
    ),
    path(
        "purchase-requests/lines/<int:line_pk>/status/",
        purchase_request_line_set_status,
        name="purchase_request_line_set_status",
    ),
]
