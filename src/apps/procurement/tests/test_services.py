from decimal import Decimal

import pytest

from apps.materials.models import Material, ProductMaterial
from apps.procurement.models import PurchaseOrder, PurchaseOrderLine, Supplier
from apps.orders.tests.conftest import UserFactory
from apps.procurement.services import receive_purchase_order_line


@pytest.mark.django_db
def test_receive_purchase_order_line_works_via_procurement_context():
    supplier = Supplier.objects.create(name="Supplier Procurement Context")
    material = Material.objects.create(name="Thread procurement")
    user = UserFactory()
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.SENT,
        created_by=user,
    )
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("5.000"),
        unit=ProductMaterial.Unit.PIECE,
        unit_price=Decimal("1.00"),
    )

    receipt_line = receive_purchase_order_line(
        purchase_order_line=line,
        quantity=Decimal("3.000"),
        received_by=user,
    )

    assert receipt_line.quantity == Decimal("3.000")
    line.refresh_from_db()
    assert line.received_quantity == Decimal("3.000")
