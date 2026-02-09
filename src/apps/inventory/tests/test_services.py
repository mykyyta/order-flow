"""Tests for inventory services."""
import pytest

from apps.inventory.models import StockMovement, StockRecord
from apps.inventory.services import add_to_stock, get_stock_quantity, remove_from_stock
from apps.orders.tests.conftest import UserFactory
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.materials.models import Material, MaterialColor


@pytest.mark.django_db
def test_get_stock_quantity_returns_zero_when_missing():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()

    assert get_stock_quantity(product_model_id=model.id, color_id=color.id) == 0


@pytest.mark.django_db
def test_add_to_stock_creates_record_and_movement():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    user = UserFactory()

    record = add_to_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=4,
        reason=StockMovement.Reason.PRODUCTION_IN,
        user=user,
    )

    assert record.quantity == 4
    assert StockRecord.objects.get(product_model=model, color=color).quantity == 4

    movement = StockMovement.objects.get(stock_record=record)
    assert movement.quantity_change == 4
    assert movement.reason == StockMovement.Reason.PRODUCTION_IN
    assert movement.created_by == user


@pytest.mark.django_db
def test_remove_from_stock_updates_quantity_and_writes_movement():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    user = UserFactory()
    add_to_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=5,
        reason=StockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    record = remove_from_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=2,
        reason=StockMovement.Reason.ORDER_OUT,
        user=user,
    )

    assert record.quantity == 3
    movements = StockMovement.objects.filter(stock_record=record).order_by("created_at")
    assert movements.count() == 2
    assert movements.last().quantity_change == -2
    assert movements.last().reason == StockMovement.Reason.ORDER_OUT


@pytest.mark.django_db
def test_remove_from_stock_raises_when_not_enough():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    user = UserFactory()
    add_to_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=1,
        reason=StockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        remove_from_stock(
            product_model_id=model.id,
            color_id=color.id,
            quantity=2,
            reason=StockMovement.Reason.ORDER_OUT,
            user=user,
        )


@pytest.mark.django_db
def test_add_and_remove_stock_by_material_colors():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    blue = MaterialColor.objects.create(material=felt, name="Blue", code=11)
    black = MaterialColor.objects.create(material=leather, name="Black", code=2)
    product = ProductModelFactory(
        is_bundle=False,
        primary_material=felt,
        secondary_material=leather,
    )
    user = UserFactory()

    add_to_stock(
        product_model_id=product.id,
        primary_material_color_id=blue.id,
        secondary_material_color_id=black.id,
        quantity=3,
        reason=StockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )
    assert (
        get_stock_quantity(
            product_model_id=product.id,
            primary_material_color_id=blue.id,
            secondary_material_color_id=black.id,
        )
        == 3
    )

    record = remove_from_stock(
        product_model_id=product.id,
        primary_material_color_id=blue.id,
        secondary_material_color_id=black.id,
        quantity=1,
        reason=StockMovement.Reason.ORDER_OUT,
        user=user,
    )
    assert record.quantity == 2
    assert (
        StockRecord.objects.get(
            product_model=product,
            primary_material_color=blue,
            secondary_material_color=black,
        ).quantity
        == 2
    )
