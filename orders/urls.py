from django.urls import path
from .views import *

urlpatterns = [
    path('', index, name='index'),
    path('orders/', order_list, name='order_list'),
    path('orders/create/', order_create, name='order_create'),
    path('orders/<uuid:order_id>/', order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/history/', order_history, name='order_history'),
    path('orders/<uuid:order_id>/update/', order_update, name='order_update'),

    path('models/', model_list, name='model_list'),
    path('models/<uuid:model_id>/', model_detail, name='model_detail'),

    path('colors/', color_list, name='color_list'),
    path('colors/<uuid:color_id>/', color_detail, name='color_detail'),

    path('login/', auth_login, name='auth_login'),
    path('logout/', auth_logout, name='auth_logout'),
    path('users/me/', auth_user, name='auth_user'),
]
