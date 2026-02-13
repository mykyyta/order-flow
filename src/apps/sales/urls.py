from django.urls import path

from apps.sales.views import customers_list

urlpatterns = [
    path("customers/", customers_list, name="customers"),
]
