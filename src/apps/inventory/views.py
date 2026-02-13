from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_products(request):
    """Placeholder view for finished products inventory."""
    return render(
        request,
        "inventory/products.html",
        {"page_title": "Готова продукція"},
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_wip(request):
    """Placeholder view for WIP (work in progress) inventory."""
    return render(
        request,
        "inventory/wip.html",
        {"page_title": "WIP"},
    )


@login_required(login_url=reverse_lazy("auth_login"))
def inventory_materials(request):
    """Placeholder view for materials inventory."""
    return render(
        request,
        "inventory/materials.html",
        {"page_title": "Матеріали"},
    )
