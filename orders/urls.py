from django.urls import path
from .views import index, auth_login, auth_logout, auth_user, ProductModelListCreateView, ColorListCreateView, \
    order_list, order_create, order_detail, order_history, order_update

urlpatterns = [
    path('', index, name='index'),
    path('orders/', order_list, name='order_list'),
    path('orders/create/', order_create, name='order_create'),
    path('orders/<uuid:order_id>/', order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/history/', order_history, name='order_history'),
    path('orders/<uuid:order_id>/update/', order_update, name='order_update'),

    path('models/', ProductModelListCreateView.as_view(), name='model_list'),

    path('colors/', ColorListCreateView.as_view(), name='color_list'),

    path('login/', auth_login, name='auth_login'),
    path('logout/', auth_logout, name='auth_logout'),
    path('users/me/', auth_user, name='auth_user'),
]
