"""Tests for procurement and material stock services."""
from decimal import Decimal

import pytest

from apps.materials.models import MaterialStockMovement, MaterialStock
from apps.materials.services import add_material_stock, remove_material_stock, receive_purchase_order_line
from apps.materials.models import (
    Material,
    MaterialUnit,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from apps.accounts.tests.conftest import UserFactory
from apps.warehouses.models import Warehouse
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_add_material_stock_creates_stock_and_movement():
    material = Material.objects.create(name="Felt", stock_unit=MaterialUnit.SQUARE_METER)
    user = UserFactory()
    warehouse = get_default_warehouse()

    stock_record = add_material_stock(
        warehouse_id=warehouse.id,
        material=material,
        quantity=Decimal("2.500"),
        unit=MaterialUnit.SQUARE_METER,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        created_by=user,
    )

    assert stock_record.quantity == Decimal("2.500")
    assert stock_record.warehouse is not None
    assert stock_record.warehouse.code == "MAIN"
    movement = MaterialStockMovement.objects.get(stock_record=stock_record)
    assert movement.quantity_change == Decimal("2.500")
    assert movement.reason == MaterialStockMovement.Reason.ADJUSTMENT_IN
    assert movement.created_by == user


@pytest.mark.django_db
def test_remove_material_stock_fails_when_not_enough():
    material = Material.objects.create(name="Leather", stock_unit=MaterialUnit.PIECE)
    warehouse = get_default_warehouse()

    add_material_stock(
        warehouse_id=warehouse.id,
        material=material,
        quantity=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        remove_material_stock(
            warehouse_id=warehouse.id,
            material=material,
            quantity=Decimal("2.000"),
            unit=MaterialUnit.PIECE,
            reason=MaterialStockMovement.Reason.PRODUCTION_OUT,
        )


@pytest.mark.django_db
def test_receive_purchase_order_line_updates_stock_and_po_status():
    supplier = Supplier.objects.create(name="Supplier Service")
    material = Material.objects.create(name="Thread", stock_unit=MaterialUnit.PIECE)
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
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("1.00"),
    )
    warehouse = get_default_warehouse()

    receipt_line = receive_purchase_order_line(
        purchase_order_line=line,
        quantity=Decimal("6.000"),
        warehouse_id=warehouse.id,
        received_by=user,
    )
    line.refresh_from_db()
    purchase_order.refresh_from_db()
    stock_record = MaterialStock.objects.get(
        material=material,
        unit=MaterialUnit.PIECE,
    )
    receipt_line.refresh_from_db()

    assert receipt_line.quantity == Decimal("6.000")
    assert receipt_line.receipt.warehouse is not None
    assert receipt_line.receipt.warehouse.code == "MAIN"
    assert line.received_quantity == Decimal("6.000")
    assert stock_record.quantity == Decimal("6.000")
    assert stock_record.warehouse is not None
    assert stock_record.warehouse.code == "MAIN"
    assert purchase_order.status == PurchaseOrder.Status.PARTIALLY_RECEIVED

    assert Warehouse.objects.filter(code="MAIN").exists()


@pytest.mark.django_db
def test_add_material_stock_rejects_unit_mismatch():
    material = Material.objects.create(name="Fabric Roll", stock_unit=MaterialUnit.METER)
    warehouse = get_default_warehouse()

    with pytest.raises(ValueError, match="Одиниця не відповідає одиниці складу матеріалу"):
        add_material_stock(
            warehouse_id=warehouse.id,
            material=material,
            quantity=Decimal("1.000"),
            unit=MaterialUnit.PIECE,
            reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        )


@pytest.mark.django_db
def test_receive_purchase_order_line_rejects_unit_mismatch():
    supplier = Supplier.objects.create(name="Supplier Units")
    user = UserFactory()
    material = Material.objects.create(name="Leather", stock_unit=MaterialUnit.SQUARE_METER)
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.SENT,
        created_by=user,
    )
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("1.00"),
    )
    warehouse = get_default_warehouse()

    with pytest.raises(ValueError, match="Одиниця в замовленні не відповідає одиниці складу матеріалу"):
        receive_purchase_order_line(
            purchase_order_line=line,
            quantity=Decimal("1.000"),
            warehouse_id=warehouse.id,
            received_by=user,
        )
