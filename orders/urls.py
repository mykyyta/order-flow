from django.urls import path
from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductModelListCreateView,
    auth_login,
    auth_logout,
    change_password,
    orders_completed,
    index,
    notification_settings,
    orders_create,
    order_detail,
    orders_active,
    orders_bulk_status,
    profile_view,
    send_delayed_notifications,
)

urlpatterns = [
    path("", index, name="index"),
    path("orders/current/", orders_active, name="orders_active"),
    path("orders/current/bulk-status/", orders_bulk_status, name="orders_bulk_status"),
    path("orders/finished/", orders_completed, name="orders_completed"),
    path("orders/create/", orders_create, name="orders_create"),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('models/', ProductModelListCreateView.as_view(), name='model_list'),
    path('colors/', ColorListCreateView.as_view(), name='color_list'),
    path('color/<int:pk>/', ColorDetailUpdateView.as_view(), name='color_detail_update'),
    path('login/', auth_login, name='auth_login'),
    path('logout/', auth_logout, name='auth_logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/change-password/', change_password, name='change_password'),
    path('profile/settings/', notification_settings, name='notification_settings'),
    path('cron/send-delayed-notifications/', send_delayed_notifications, name='send_delayed_notifications')

]
