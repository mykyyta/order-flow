from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy


@login_required(login_url=reverse_lazy("auth_login"))
def customers_list(request):
    """Placeholder view for customers list."""
    return render(
        request,
        "sales/customers.html",
        {"page_title": "Клієнти"},
    )
