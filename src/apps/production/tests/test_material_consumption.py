from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.tests.conftest import UserFactory
from apps.catalog.models import ProductMaterial, Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.materials.models import Material, MaterialStock, MaterialStockMovement, MaterialUnit
from apps.materials.services import add_material_stock
from apps.production.domain.status import STATUS_IN_PROGRESS, STATUS_NEW
from apps.production.services import change_production_order_status, create_production_order
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_production_in_progress_consumes_materials():
    user = UserFactory()
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Leather for production", stock_unit=MaterialUnit.PIECE)
    product = ProductFactory(kind="standard")
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
    )
    variant = Variant.objects.create(product=product, color=ColorFactory())
    add_material_stock(
        material=material,
        quantity=Decimal("5.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        order = create_production_order(
            product=product,
            variant=variant,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment="consume materials",
            created_by=user,
            orders_url=None,
        )

    change_production_order_status(
        production_orders=[order],
        new_status=STATUS_IN_PROGRESS,
        changed_by=user,
    )

    order.refresh_from_db()
    assert order.status == STATUS_IN_PROGRESS
    assert order.materials_consumed_at is not None
    stock = MaterialStock.objects.get(
        warehouse=warehouse,
        material=material,
        unit=MaterialUnit.PIECE,
        material_color__isnull=True,
    )
    assert stock.quantity == Decimal("3.000")
    movement = MaterialStockMovement.objects.filter(stock_record=stock).latest("created_at")
    assert movement.reason == MaterialStockMovement.Reason.PRODUCTION_OUT


@pytest.mark.django_db
def test_production_in_progress_raises_when_not_enough_materials():
    user = UserFactory()
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Not enough material", stock_unit=MaterialUnit.PIECE)
    product = ProductFactory(kind="standard")
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
    )
    variant = Variant.objects.create(product=product, color=ColorFactory())
    add_material_stock(
        material=material,
        quantity=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        order = create_production_order(
            product=product,
            variant=variant,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment="missing materials",
            created_by=user,
            orders_url=None,
        )

    with pytest.raises(ValueError, match="Недостатньо матеріалів"):
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_IN_PROGRESS,
            changed_by=user,
        )

    order.refresh_from_db()
    assert order.status == STATUS_NEW
    assert order.materials_consumed_at is None
