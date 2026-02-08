from django.urls import path

from .views import (
    order_detail,
    order_edit,
    orders_active,
    orders_bulk_status,
    orders_completed,
    orders_create,
    palette_lab,
    send_delayed_notifications,
)

urlpatterns = [
    path("", orders_active, name="index"),
    path("palette/", palette_lab, name="palette_lab"),
    path("orders/current/", orders_active, name="orders_active"),
    path("orders/current/bulk-status/", orders_bulk_status, name="orders_bulk_status"),
    path("orders/finished/", orders_completed, name="orders_completed"),
    path("orders/create/", orders_create, name="orders_create"),
    path("orders/<int:order_id>/", order_detail, name="order_detail"),
    path("orders/<int:order_id>/edit/", order_edit, name="order_edit"),
    path(
        "cron/send-delayed-notifications/",
        send_delayed_notifications,
        name="send_delayed_notifications",
    ),
]
