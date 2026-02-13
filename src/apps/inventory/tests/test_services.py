"""Tests for inventory services."""
import pytest
from django.db import IntegrityError

from apps.catalog.models import Variant
from apps.inventory.models import ProductStockTransfer, ProductStockMovement, ProductStock
from apps.inventory.services import (
    add_to_stock,
    get_stock_quantity,
    remove_from_stock,
    transfer_finished_stock,
)
from apps.accounts.tests.conftest import UserFactory
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.materials.models import Material, MaterialColor
from apps.warehouses.models import Warehouse
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_get_stock_quantity_returns_zero_when_missing():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    warehouse = get_default_warehouse()

    assert get_stock_quantity(warehouse_id=warehouse.id, product_id=model.id, color_id=color.id) == 0


@pytest.mark.django_db
def test_add_to_stock_creates_record_and_movement():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    user = UserFactory()
    warehouse = get_default_warehouse()

    record = add_to_stock(
        warehouse_id=warehouse.id,
        product_id=model.id,
        color_id=color.id,
        quantity=4,
        reason=ProductStockMovement.Reason.PRODUCTION_IN,
        user=user,
    )

    assert record.quantity == 4
    assert record.warehouse is not None
    assert record.warehouse.code == "MAIN"
    assert record.variant is not None
    assert record.variant.product_id == model.id
    assert record.variant.color_id == color.id
    assert ProductStock.objects.get(warehouse=warehouse, variant=record.variant).quantity == 4

    movement = ProductStockMovement.objects.get(stock_record=record)
    assert movement.quantity_change == 4
    assert movement.reason == ProductStockMovement.Reason.PRODUCTION_IN
    assert movement.created_by == user


@pytest.mark.django_db
def test_remove_from_stock_updates_quantity_and_writes_movement():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    user = UserFactory()
    warehouse = get_default_warehouse()
    add_to_stock(
        warehouse_id=warehouse.id,
        product_id=model.id,
        color_id=color.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    record = remove_from_stock(
        warehouse_id=warehouse.id,
        product_id=model.id,
        color_id=color.id,
        quantity=2,
        reason=ProductStockMovement.Reason.ORDER_OUT,
        user=user,
    )

    assert record.quantity == 3
    movements = ProductStockMovement.objects.filter(stock_record=record).order_by("created_at")
    assert movements.count() == 2
    assert movements.last().quantity_change == -2
    assert movements.last().reason == ProductStockMovement.Reason.ORDER_OUT


@pytest.mark.django_db
def test_remove_from_stock_raises_when_not_enough():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    user = UserFactory()
    warehouse = get_default_warehouse()
    add_to_stock(
        warehouse_id=warehouse.id,
        product_id=model.id,
        color_id=color.id,
        quantity=1,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        remove_from_stock(
            warehouse_id=warehouse.id,
            product_id=model.id,
            color_id=color.id,
            quantity=2,
            reason=ProductStockMovement.Reason.ORDER_OUT,
            user=user,
        )


@pytest.mark.django_db
def test_add_and_remove_stock_by_material_colors():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    blue = MaterialColor.objects.create(material=felt, name="Blue", code=11)
    black = MaterialColor.objects.create(material=leather, name="Black", code=2)
    product = ProductFactory(
        kind="standard",
        primary_material=felt,
        secondary_material=leather,
    )
    user = UserFactory()
    warehouse = get_default_warehouse()

    add_to_stock(
        warehouse_id=warehouse.id,
        product_id=product.id,
        primary_material_color_id=blue.id,
        secondary_material_color_id=black.id,
        quantity=3,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )
    assert (
        get_stock_quantity(
            warehouse_id=warehouse.id,
            product_id=product.id,
            primary_material_color_id=blue.id,
            secondary_material_color_id=black.id,
        )
        == 3
    )

    record = remove_from_stock(
        warehouse_id=warehouse.id,
        product_id=product.id,
        primary_material_color_id=blue.id,
        secondary_material_color_id=black.id,
        quantity=1,
        reason=ProductStockMovement.Reason.ORDER_OUT,
        user=user,
    )
    assert record.quantity == 2
    assert (
        ProductStock.objects.get(
            warehouse=warehouse,
            variant=record.variant,
        ).quantity
        == 2
    )


@pytest.mark.django_db
def test_stock_record_requires_warehouse():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(
        product=model,
        color=color,
    )

    with pytest.raises(IntegrityError):
        ProductStock.objects.create(
            variant=variant,
            quantity=1,
        )


@pytest.mark.django_db
def test_stock_record_requires_variant():
    warehouse = Warehouse.objects.create(
        name="Variant Required Warehouse",
        code="INV-VARIANT-REQ",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(IntegrityError):
        ProductStock.objects.create(
            warehouse=warehouse,
            quantity=1,
        )


@pytest.mark.django_db
def test_get_stock_quantity_accepts_variant_id():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    user = UserFactory()
    warehouse = get_default_warehouse()

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=2,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    assert get_stock_quantity(warehouse_id=warehouse.id, variant_id=variant.id) == 2


@pytest.mark.django_db
def test_add_to_stock_accepts_variant_id_without_legacy_fields():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    user = UserFactory()
    warehouse = get_default_warehouse()

    record = add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=3,
        reason=ProductStockMovement.Reason.PRODUCTION_IN,
        user=user,
    )

    assert record.variant_id == variant.id
    assert record.quantity == 3


@pytest.mark.django_db
def test_remove_from_stock_accepts_variant_id():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    user = UserFactory()
    warehouse = get_default_warehouse()

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )
    record = remove_from_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=2,
        reason=ProductStockMovement.Reason.ORDER_OUT,
        user=user,
    )

    assert record.quantity == 3


@pytest.mark.django_db
def test_add_to_stock_supports_multiple_warehouses():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    user = UserFactory()
    main = Warehouse.objects.create(
        name="Main Warehouse",
        code="MAIN-2",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    retail = Warehouse.objects.create(
        name="Retail Warehouse",
        code="RETAIL",
        kind=Warehouse.Kind.RETAIL,
        is_default_for_production=False,
        is_active=True,
    )

    add_to_stock(
        warehouse_id=main.id,
        product_id=model.id,
        color_id=color.id,
        quantity=3,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )
    add_to_stock(
        warehouse_id=retail.id,
        product_id=model.id,
        color_id=color.id,
        quantity=4,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    assert (
        ProductStock.objects.get(warehouse=main, variant__product=model, variant__color=color).quantity
        == 3
    )
    assert (
        ProductStock.objects.get(
            warehouse=retail,
            variant__product=model,
            variant__color=color,
        ).quantity
        == 4
    )


@pytest.mark.django_db
def test_transfer_finished_stock_moves_between_warehouses():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    user = UserFactory()
    from_warehouse = Warehouse.objects.create(
        name="From Finished",
        code="FIN-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Finished",
        code="FIN-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    add_to_stock(
        warehouse_id=from_warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    transfer = transfer_finished_stock(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
        variant_id=variant.id,
        quantity=2,
        user=user,
        notes="Move to retail",
    )

    assert transfer.status == transfer.Status.COMPLETED
    assert transfer.lines.count() == 1
    assert transfer.lines.first().quantity == 2
    assert get_stock_quantity(warehouse_id=from_warehouse.id, variant_id=variant.id) == 3
    assert get_stock_quantity(warehouse_id=to_warehouse.id, variant_id=variant.id) == 2

    out_movement = ProductStockMovement.objects.filter(
        stock_record__warehouse_id=from_warehouse.id,
        stock_record__variant_id=variant.id,
    ).latest("created_at")
    in_movement = ProductStockMovement.objects.filter(
        stock_record__warehouse_id=to_warehouse.id,
        stock_record__variant_id=variant.id,
    ).latest("created_at")
    assert out_movement.reason == ProductStockMovement.Reason.TRANSFER_OUT
    assert in_movement.reason == ProductStockMovement.Reason.TRANSFER_IN
    assert out_movement.related_transfer == transfer
    assert in_movement.related_transfer == transfer


@pytest.mark.django_db
def test_transfer_finished_stock_requires_different_warehouses():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    warehouse = Warehouse.objects.create(
        name="Transfer Same",
        code="FIN-SAME",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(ValueError, match="must be different"):
        transfer_finished_stock(
            from_warehouse_id=warehouse.id,
            to_warehouse_id=warehouse.id,
            variant_id=variant.id,
            quantity=1,
        )


@pytest.mark.django_db
def test_transfer_finished_stock_rolls_back_when_not_enough_stock():
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=model, color=color)
    from_warehouse = Warehouse.objects.create(
        name="From Finished Empty",
        code="FIN-EMPTY",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Finished Empty",
        code="FIN-EMPTY-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        transfer_finished_stock(
            from_warehouse_id=from_warehouse.id,
            to_warehouse_id=to_warehouse.id,
            variant_id=variant.id,
            quantity=1,
        )

    assert get_stock_quantity(warehouse_id=to_warehouse.id, variant_id=variant.id) == 0
    assert not ProductStockTransfer.objects.filter(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
    ).exists()
    assert not ProductStockMovement.objects.filter(
        stock_record__warehouse_id=to_warehouse.id,
        stock_record__variant_id=variant.id,
    ).exists()
