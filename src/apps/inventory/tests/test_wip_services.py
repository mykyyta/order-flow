import pytest

from apps.catalog.models import ProductVariant
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.inventory.models import WIPStockMovement, WIPStockRecord
from apps.inventory.services import add_to_wip_stock, get_wip_stock_quantity, remove_from_wip_stock
from apps.orders.tests.conftest import UserFactory
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_add_to_wip_stock_creates_record_and_movement():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    variant = ProductVariant.objects.create(product=model, color=color)
    user = UserFactory()

    record = add_to_wip_stock(
        product_variant_id=variant.id,
        quantity=3,
        reason=WIPStockMovement.Reason.CUTTING_IN,
        user=user,
    )

    assert record.quantity == 3
    assert record.warehouse.code == "MAIN"
    movement = WIPStockMovement.objects.get(stock_record=record)
    assert movement.quantity_change == 3
    assert movement.reason == WIPStockMovement.Reason.CUTTING_IN
    assert movement.created_by == user


@pytest.mark.django_db
def test_remove_from_wip_stock_updates_quantity_and_movement():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    variant = ProductVariant.objects.create(product=model, color=color)
    user = UserFactory()
    add_to_wip_stock(
        product_variant_id=variant.id,
        quantity=4,
        reason=WIPStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    record = remove_from_wip_stock(
        product_variant_id=variant.id,
        quantity=1,
        reason=WIPStockMovement.Reason.FINISHING_OUT,
        user=user,
    )
    assert record.quantity == 3
    assert get_wip_stock_quantity(product_variant_id=variant.id) == 3


@pytest.mark.django_db
def test_remove_from_wip_stock_fails_when_not_enough():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    variant = ProductVariant.objects.create(product=model, color=color)
    user = UserFactory()

    add_to_wip_stock(
        product_variant_id=variant.id,
        quantity=1,
        reason=WIPStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    with pytest.raises(ValueError, match="Недостатньо WIP"):
        remove_from_wip_stock(
            product_variant_id=variant.id,
            quantity=2,
            reason=WIPStockMovement.Reason.SCRAP_OUT,
            user=user,
        )


@pytest.mark.django_db
def test_wip_stock_split_by_warehouse():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    variant = ProductVariant.objects.create(product=model, color=color)
    user = UserFactory()
    wh_a = Warehouse.objects.create(
        name="WIP A",
        code="WIP-A",
        kind=Warehouse.Kind.PRODUCTION,
        is_default_for_production=False,
        is_active=True,
    )
    wh_b = Warehouse.objects.create(
        name="WIP B",
        code="WIP-B",
        kind=Warehouse.Kind.PRODUCTION,
        is_default_for_production=False,
        is_active=True,
    )

    add_to_wip_stock(
        warehouse_id=wh_a.id,
        product_variant_id=variant.id,
        quantity=2,
        reason=WIPStockMovement.Reason.CUTTING_IN,
        user=user,
    )
    add_to_wip_stock(
        warehouse_id=wh_b.id,
        product_variant_id=variant.id,
        quantity=5,
        reason=WIPStockMovement.Reason.CUTTING_IN,
        user=user,
    )

    assert get_wip_stock_quantity(warehouse_id=wh_a.id, product_variant_id=variant.id) == 2
    assert get_wip_stock_quantity(warehouse_id=wh_b.id, product_variant_id=variant.id) == 5
    assert WIPStockRecord.objects.filter(product_variant=variant).count() == 2
