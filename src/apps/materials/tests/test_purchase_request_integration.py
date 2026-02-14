from decimal import Decimal

import pytest

from apps.accounts.tests.conftest import UserFactory
from apps.materials.models import (
    Material,
    MaterialUnit,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from apps.materials.services import receive_purchase_order_line
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_receive_purchase_order_line_marks_request_line_done_when_quantity_unknown():
    from apps.materials.models import PurchaseRequest, PurchaseRequestLine

    user = UserFactory()
    warehouse = get_default_warehouse()
    supplier = Supplier.objects.create(name="Shop A")
    material = Material.objects.create(name="Thread", stock_unit=MaterialUnit.PIECE)

    request = PurchaseRequest.objects.create(created_by=user, warehouse=warehouse)
    request_line = PurchaseRequestLine.objects.create(
        request=request,
        material=material,
        requested_quantity=None,
        unit=None,
    )

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    po_line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("5.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("1.00"),
        request_line=request_line,
    )

    receive_purchase_order_line(
        purchase_order_line=po_line,
        quantity=Decimal("1.000"),
        warehouse_id=warehouse.id,
        received_by=user,
    )

    request_line.refresh_from_db()
    assert request_line.status == PurchaseRequestLine.Status.DONE


@pytest.mark.django_db
def test_receive_purchase_order_line_marks_request_line_done_when_requested_quantity_reached():
    from apps.materials.models import PurchaseRequest, PurchaseRequestLine

    user = UserFactory()
    warehouse = get_default_warehouse()
    supplier = Supplier.objects.create(name="Shop B")
    material = Material.objects.create(name="Glue", stock_unit=MaterialUnit.MILLILITER)

    request = PurchaseRequest.objects.create(created_by=user, warehouse=warehouse)
    request_line = PurchaseRequestLine.objects.create(
        request=request,
        material=material,
        requested_quantity=Decimal("3.000"),
        unit=MaterialUnit.MILLILITER,
    )

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    po_line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("10.000"),
        unit=MaterialUnit.MILLILITER,
        unit_price=Decimal("2.00"),
        request_line=request_line,
    )

    receive_purchase_order_line(
        purchase_order_line=po_line,
        quantity=Decimal("2.000"),
        warehouse_id=warehouse.id,
        received_by=user,
    )
    request_line.refresh_from_db()
    assert request_line.status == PurchaseRequestLine.Status.OPEN

    receive_purchase_order_line(
        purchase_order_line=po_line,
        quantity=Decimal("1.000"),
        warehouse_id=warehouse.id,
        received_by=user,
    )
    request_line.refresh_from_db()
    assert request_line.status == PurchaseRequestLine.Status.DONE
