"""Tests for procurement and material stock services."""
from decimal import Decimal

import pytest

from apps.materials.models import (
    Material,
    MaterialMovement,
    MaterialStockRecord,
    ProductMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from apps.materials.procurement_services import (
    add_material_stock,
    receive_purchase_order_line,
    remove_material_stock,
)
from apps.orders.tests.conftest import UserFactory


@pytest.mark.django_db
def test_add_material_stock_creates_stock_and_movement():
    material = Material.objects.create(name="Felt")
    user = UserFactory()

    stock_record = add_material_stock(
        material=material,
        quantity=Decimal("2.500"),
        unit=ProductMaterial.Unit.SQUARE_METER,
        reason=MaterialMovement.Reason.ADJUSTMENT_IN,
        created_by=user,
    )

    assert stock_record.quantity == Decimal("2.500")
    movement = MaterialMovement.objects.get(stock_record=stock_record)
    assert movement.quantity_change == Decimal("2.500")
    assert movement.reason == MaterialMovement.Reason.ADJUSTMENT_IN
    assert movement.created_by == user


@pytest.mark.django_db
def test_remove_material_stock_fails_when_not_enough():
    material = Material.objects.create(name="Leather")

    add_material_stock(
        material=material,
        quantity=Decimal("1.000"),
        unit=ProductMaterial.Unit.PIECE,
        reason=MaterialMovement.Reason.ADJUSTMENT_IN,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        remove_material_stock(
            material=material,
            quantity=Decimal("2.000"),
            unit=ProductMaterial.Unit.PIECE,
            reason=MaterialMovement.Reason.PRODUCTION_OUT,
        )


@pytest.mark.django_db
def test_receive_purchase_order_line_updates_stock_and_po_status():
    supplier = Supplier.objects.create(name="Supplier Service")
    material = Material.objects.create(name="Thread")
    user = UserFactory()
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.SENT,
        created_by=user,
    )
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("10.000"),
        unit=ProductMaterial.Unit.PIECE,
        unit_price=Decimal("1.00"),
    )

    receipt_line = receive_purchase_order_line(
        purchase_order_line=line,
        quantity=Decimal("6.000"),
        received_by=user,
    )
    line.refresh_from_db()
    purchase_order.refresh_from_db()
    stock_record = MaterialStockRecord.objects.get(
        material=material,
        unit=ProductMaterial.Unit.PIECE,
    )

    assert receipt_line.quantity == Decimal("6.000")
    assert line.received_quantity == Decimal("6.000")
    assert stock_record.quantity == Decimal("6.000")
    assert purchase_order.status == PurchaseOrder.Status.PARTIALLY_RECEIVED
