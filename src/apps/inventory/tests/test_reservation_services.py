import pytest

from apps.catalog.models import Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.inventory.models import ProductStockMovement, ProductStockReservation
from apps.inventory.services import (
    add_to_stock,
    get_available_stock_quantity,
    get_reserved_stock_quantity,
    remove_from_stock,
    reserve_stock_up_to,
    release_reservations_for_sales_order_line,
)
from apps.sales.models import SalesOrder, SalesOrderLine
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_get_reserved_and_available_stock_quantity():
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=product, color=color)

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Reserved test")
    line = SalesOrderLine.objects.create(sales_order=order, product=product, variant=variant, quantity=1)
    ProductStockReservation.objects.create(
        warehouse=warehouse,
        variant=variant,
        sales_order_line=line,
        quantity=2,
    )

    assert get_reserved_stock_quantity(warehouse_id=warehouse.id, variant_id=variant.id) == 2
    assert get_available_stock_quantity(warehouse_id=warehouse.id, variant_id=variant.id) == 3


@pytest.mark.django_db
def test_reserve_stock_up_to_respects_other_reservations():
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
    )

    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Reserve up to")
    line1 = SalesOrderLine.objects.create(sales_order=order, product=product, variant=variant, quantity=1)
    line2 = SalesOrderLine.objects.create(sales_order=order, product=product, variant=variant, quantity=1)

    assert reserve_stock_up_to(
        warehouse_id=warehouse.id,
        sales_order_line_id=line1.id,
        variant_id=variant.id,
        quantity=4,
    ) == 4
    assert reserve_stock_up_to(
        warehouse_id=warehouse.id,
        sales_order_line_id=line2.id,
        variant_id=variant.id,
        quantity=4,
    ) == 1

    assert (
        ProductStockReservation.objects.get(
            sales_order_line=line1,
            variant=variant,
            warehouse=warehouse,
            status=ProductStockReservation.Status.ACTIVE,
        ).quantity
        == 4
    )
    assert (
        ProductStockReservation.objects.get(
            sales_order_line=line2,
            variant=variant,
            warehouse=warehouse,
            status=ProductStockReservation.Status.ACTIVE,
        ).quantity
        == 1
    )
    assert get_available_stock_quantity(warehouse_id=warehouse.id, variant_id=variant.id) == 0


@pytest.mark.django_db
def test_release_reservations_for_sales_order_line():
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())
    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Release test")
    line = SalesOrderLine.objects.create(sales_order=order, product=product, variant=variant, quantity=1)
    reservation = ProductStockReservation.objects.create(
        warehouse=warehouse,
        variant=variant,
        sales_order_line=line,
        quantity=2,
    )

    assert release_reservations_for_sales_order_line(sales_order_line_id=line.id) == 1
    reservation.refresh_from_db()
    assert reservation.status == ProductStockReservation.Status.RELEASED


@pytest.mark.django_db
def test_remove_from_stock_rejects_reserved_quantity():
    warehouse = get_default_warehouse()
    product = ProductFactory(kind="standard")
    variant = Variant.objects.create(product=product, color=ColorFactory())
    order = SalesOrder.objects.create(source=SalesOrder.Source.SITE, customer_info="Reserved removal")
    line = SalesOrderLine.objects.create(sales_order=order, product=product, variant=variant, quantity=1)

    add_to_stock(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=5,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
    )
    reserve_stock_up_to(
        warehouse_id=warehouse.id,
        sales_order_line_id=line.id,
        variant_id=variant.id,
        quantity=4,
    )

    with pytest.raises(ValueError, match="забронь"):
        remove_from_stock(
            warehouse_id=warehouse.id,
            variant_id=variant.id,
            quantity=2,
            reason=ProductStockMovement.Reason.ADJUSTMENT_OUT,
        )
