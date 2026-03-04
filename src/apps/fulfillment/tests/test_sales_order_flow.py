from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.tests.conftest import UserFactory
from apps.catalog.models import ProductMaterial, Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.fulfillment.services import (
    create_make_to_stock_production_orders,
    plan_sales_order,
    ship_sales_order,
)
from apps.fulfillment.services import complete_production_order
from apps.inventory.models import ProductStockMovement, ProductStockReservation, ProductStock
from apps.inventory.services import add_to_stock
from apps.materials.models import Material, MaterialStockMovement, MaterialUnit
from apps.materials.services import add_material_stock
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBlocker
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_plan_sales_order_reserves_stock_and_sets_ready():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())
    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Plan reserve")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=2,
        production_mode=SalesOrderLine.ProductionMode.AUTO,
    )

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=2,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    result = plan_sales_order(sales_order=order, planned_by=user)
    assert result["created_production_orders"] == 0

    order.refresh_from_db()
    assert order.status == SalesOrder.Status.READY
    assert (
        ProductStockReservation.objects.get(
            warehouse=warehouse,
            variant=variant,
            sales_order_line=line,
            status=ProductStockReservation.Status.ACTIVE,
        ).quantity
        == 2
    )


@pytest.mark.django_db
def test_plan_sales_order_creates_production_for_deficit_when_materials_enough():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Thread for plan", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("10.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Plan produce")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=2,
        production_mode=SalesOrderLine.ProductionMode.AUTO,
    )

    with patch("apps.production.services.send_order_created"):
        result = plan_sales_order(sales_order=order, planned_by=user)

    assert result["created_production_orders"] == 2
    assert line.production_orders.count() == 2

    order.refresh_from_db()
    assert order.status == SalesOrder.Status.PRODUCTION
    assert not SalesOrderLineBlocker.objects.filter(sales_order_line=line, is_active=True).exists()


@pytest.mark.django_db
def test_plan_sales_order_sets_blocker_when_missing_materials_and_does_not_create_production():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Missing material", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Plan missing")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=1,
        production_mode=SalesOrderLine.ProductionMode.AUTO,
    )

    with patch("apps.production.services.send_order_created"):
        result = plan_sales_order(sales_order=order, planned_by=user)

    assert result["created_production_orders"] == 0
    assert line.production_orders.count() == 0
    assert SalesOrderLineBlocker.objects.filter(
        sales_order_line=line,
        code=SalesOrderLineBlocker.Code.MISSING_MATERIALS,
        is_active=True,
    ).exists()

    order.refresh_from_db()
    assert order.status == SalesOrder.Status.PROCESSING


@pytest.mark.django_db
def test_plan_sales_order_force_production_ignores_stock():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Force material", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("10.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )
    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Force")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=2,
        production_mode=SalesOrderLine.ProductionMode.FORCE,
    )

    with patch("apps.production.services.send_order_created"):
        result = plan_sales_order(sales_order=order, planned_by=user)

    assert result["created_production_orders"] == 2
    assert line.production_orders.count() == 2
    assert not ProductStockReservation.objects.filter(sales_order_line=line).exists()

    order.refresh_from_db()
    assert order.status == SalesOrder.Status.PRODUCTION


@pytest.mark.django_db
def test_ship_sales_order_consumes_reservations_and_removes_stock():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())
    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Ship")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=2,
        production_mode=SalesOrderLine.ProductionMode.AUTO,
    )
    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=2,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    plan_sales_order(sales_order=order, planned_by=user)
    order.refresh_from_db()
    assert order.status == SalesOrder.Status.READY

    ship_sales_order(sales_order=order, shipped_by=user)

    order.refresh_from_db()
    assert order.status == SalesOrder.Status.SHIPPED
    assert ProductStock.objects.get(warehouse=warehouse, variant=variant).quantity == 0
    res = ProductStockReservation.objects.get(
        sales_order_line=line,
        variant=variant,
        warehouse=warehouse,
    )
    assert res.status == ProductStockReservation.Status.CONSUMED
    movement = ProductStockMovement.objects.filter(stock_record__variant=variant, stock_record__warehouse=warehouse).latest(
        "created_at"
    )
    assert movement.reason == ProductStockMovement.Reason.ORDER_OUT


@pytest.mark.django_db
def test_plan_sales_order_is_idempotent_and_completion_reserves_stock():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Idempotent material", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("10.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Idempotent plan")
    line = SalesOrderLine.objects.create(
        sales_order=order,
        product=product,
        variant=variant,
        quantity=2,
        production_mode=SalesOrderLine.ProductionMode.AUTO,
    )

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        result1 = plan_sales_order(sales_order=order, planned_by=user)
        result2 = plan_sales_order(sales_order=order, planned_by=user)

        assert result1["created_production_orders"] == 2
        assert result2["created_production_orders"] == 0
        assert line.production_orders.exclude(status="done").count() == 2

        first_order = line.production_orders.exclude(status="done").first()
        complete_production_order(production_order=first_order, changed_by=user)

    # One item produced, plan after completion should reserve it for the order.
    assert ProductStock.objects.get(warehouse=warehouse, variant=variant).quantity == 1
    reservation = ProductStockReservation.objects.get(
        warehouse=warehouse,
        variant=variant,
        sales_order_line=line,
        status=ProductStockReservation.Status.ACTIVE,
    )
    assert reservation.quantity == 1


@pytest.mark.django_db
def test_make_to_stock_creates_production_orders_when_materials_enough():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Make-to-stock material", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("10.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        orders = create_make_to_stock_production_orders(
            variant_id=variant.id,
            quantity=2,
            created_by=user,
        )

    assert len(orders) == 2
    assert all(o.sales_order_line_id is None for o in orders)


@pytest.mark.django_db
def test_make_to_stock_raises_when_missing_materials():
    user = UserFactory()
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    material = Material.objects.create(name="Make-to-stock missing", stock_unit=MaterialUnit.PIECE)
    ProductMaterial.objects.create(
        product=product,
        material=material,
        role=ProductMaterial.Role.OTHER,
        quantity_per_unit=Decimal("5.000"),
        unit=MaterialUnit.PIECE,
    )
    add_material_stock(
        material=material,
        quantity=Decimal("1.000"),
        unit=MaterialUnit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        warehouse_id=warehouse.id,
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        with pytest.raises(ValueError, match="Недостатньо матеріалів"):
            create_make_to_stock_production_orders(
                variant_id=variant.id,
                quantity=1,
                created_by=user,
            )
