from django.urls import path
from .views import (
    ColorDetailUpdateView,
    ColorListCreateView,
    ProductModelListCreateView,
    auth_login,
    auth_logout,
    change_password,
    finished_orders_list,
    index,
    notification_settings,
    order_create,
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
    path('orders/finished/', finished_orders_list, name='finished_orders_list'),
    path('orders/create/', order_create, name='order_create'),
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
