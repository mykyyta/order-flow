from decimal import Decimal

import pytest

from apps.material_inventory.models import MaterialStockMovement, MaterialStockTransfer
from apps.material_inventory.services import (
    add_material_stock,
    remove_material_stock,
    transfer_material_stock,
)
from apps.materials.models import Material, MaterialMovement, ProductMaterial
from apps.accounts.tests.conftest import UserFactory
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_add_and_remove_material_stock_via_material_inventory_context():
    material = Material.objects.create(name="Leather material inventory")
    user = UserFactory()

    stock_record = add_material_stock(
        material=material,
        quantity=Decimal("4.000"),
        unit=ProductMaterial.Unit.PIECE,
        reason=MaterialMovement.Reason.ADJUSTMENT_IN,
        created_by=user,
    )
    assert stock_record.quantity == Decimal("4.000")

    stock_record = remove_material_stock(
        material=material,
        quantity=Decimal("1.500"),
        unit=ProductMaterial.Unit.PIECE,
        reason=MaterialMovement.Reason.PRODUCTION_OUT,
        created_by=user,
    )
    assert stock_record.quantity == Decimal("2.500")


@pytest.mark.django_db
def test_transfer_material_stock_moves_between_warehouses():
    material = Material.objects.create(name="Leather transfer service")
    user = UserFactory()
    from_warehouse = Warehouse.objects.create(
        name="From Material Service",
        code="MAT-SVC-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Material Service",
        code="MAT-SVC-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    add_material_stock(
        warehouse_id=from_warehouse.id,
        material=material,
        quantity=Decimal("6.000"),
        unit=ProductMaterial.Unit.PIECE,
        reason=MaterialMovement.Reason.ADJUSTMENT_IN,
        created_by=user,
    )

    transfer = transfer_material_stock(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
        material=material,
        quantity=Decimal("2.500"),
        unit=ProductMaterial.Unit.PIECE,
        created_by=user,
        notes="Transfer to workshop",
    )

    assert transfer.status == transfer.Status.COMPLETED
    assert transfer.lines.count() == 1
    assert transfer.lines.first().quantity == Decimal("2.500")

    from_record = transfer.lines.first().material.stock_records.get(warehouse_id=from_warehouse.id)
    to_record = transfer.lines.first().material.stock_records.get(warehouse_id=to_warehouse.id)
    assert from_record.quantity == Decimal("3.500")
    assert to_record.quantity == Decimal("2.500")

    out_movement = MaterialStockMovement.objects.filter(stock_record=from_record).latest("created_at")
    in_movement = MaterialStockMovement.objects.filter(stock_record=to_record).latest("created_at")
    assert out_movement.reason == MaterialStockMovement.Reason.TRANSFER_OUT
    assert in_movement.reason == MaterialStockMovement.Reason.TRANSFER_IN
    assert out_movement.related_transfer == transfer
    assert in_movement.related_transfer == transfer


@pytest.mark.django_db
def test_transfer_material_stock_requires_different_warehouses():
    material = Material.objects.create(name="Leather transfer same")
    warehouse = Warehouse.objects.create(
        name="Same Material Service",
        code="MAT-SVC-SAME",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(ValueError, match="must be different"):
        transfer_material_stock(
            from_warehouse_id=warehouse.id,
            to_warehouse_id=warehouse.id,
            material=material,
            quantity=Decimal("1.000"),
            unit=ProductMaterial.Unit.PIECE,
        )


@pytest.mark.django_db
def test_transfer_material_stock_rolls_back_when_not_enough_stock():
    material = Material.objects.create(name="Leather transfer rollback")
    from_warehouse = Warehouse.objects.create(
        name="From Material Empty",
        code="MAT-SVC-EMPTY",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Material Empty",
        code="MAT-SVC-EMPTY-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        transfer_material_stock(
            from_warehouse_id=from_warehouse.id,
            to_warehouse_id=to_warehouse.id,
            material=material,
            quantity=Decimal("1.000"),
            unit=ProductMaterial.Unit.PIECE,
        )

    assert not MaterialStockTransfer.objects.filter(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
    ).exists()
    assert not MaterialStockMovement.objects.filter(
        stock_record__warehouse_id=to_warehouse.id,
        stock_record__material_id=material.id,
    ).exists()
