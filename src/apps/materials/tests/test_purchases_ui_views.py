from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.tests.conftest import UserFactory
from apps.materials.models import (
    Material,
    MaterialStock,
    MaterialUnit,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    Supplier,
)
from apps.warehouses.services import get_default_warehouse


AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.mark.django_db(transaction=True)
def test_purchases_list_renders_purchase_orders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop UI")
    PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)

    response = client.get(reverse("purchases"))
    assert response.status_code == 200
    assert supplier.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_detail_renders_lines_and_receive_link(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop Detail")
    material = Material.objects.create(name="Leather", stock_unit=MaterialUnit.PIECE)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("10.00"),
    )

    response = client.get(reverse("purchase_detail", kwargs={"pk": po.pk}))
    assert response.status_code == 200
    assert material.name.encode() in response.content
    assert reverse("purchase_line_receive", kwargs={"pk": po.pk, "line_pk": line.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_line_receive_adds_stock(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    supplier = Supplier.objects.create(name="Shop Receive")
    material = Material.objects.create(name="Thread", stock_unit=MaterialUnit.PIECE)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("5.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("1.00"),
    )

    response = client.post(
        reverse("purchase_line_receive", kwargs={"pk": po.pk, "line_pk": line.pk}),
        data={"quantity": "2.000", "notes": "ok"},
    )
    assert response.status_code == 302

    stock = MaterialStock.objects.get(warehouse=warehouse, material=material, unit=MaterialUnit.PIECE)
    assert stock.quantity == Decimal("2.000")


@pytest.mark.django_db(transaction=True)
def test_purchase_requests_list_renders_requests(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user, notes="Need stuff")

    response = client.get(reverse("purchase_requests"))
    assert response.status_code == 200
    assert f"Заявка #{pr.id}".encode() in response.content
