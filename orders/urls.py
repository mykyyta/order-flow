from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name='index'),
    path('orders/current/', current_orders_list, name='current_orders_list'),
    path('orders/finished/', finished_orders_list, name='finished_orders_list'),
    path('orders/create/', order_create, name='order_create'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/<int:order_id>/history/', order_history, name='order_history'),
    path('orders/<int:order_id>/update/', order_update, name='order_update'),
    path('models/', ProductModelListCreateView.as_view(), name='model_list'),
    path('colors/', ColorListCreateView.as_view(), name='color_list'),
    path('color/<int:pk>/', ColorDetailUpdateView.as_view(), name='color_detail_update'),

    path('login/', auth_login, name='auth_login'),
    path('logout/', auth_logout, name='auth_logout'),
    path('users/me/', auth_user, name='auth_user'),
]
