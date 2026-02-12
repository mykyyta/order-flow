"""Tests for product material requirements service."""
from decimal import Decimal

import pytest

from apps.catalog.models import BundleComponent, Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.materials.models import Material, BOM
from apps.materials.services import calculate_material_requirements_for_sales_order_line
from apps.sales.models import SalesOrder, SalesOrderLine


@pytest.mark.django_db
def test_calculate_material_requirements_for_single_product_line():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    product = ProductFactory(name="Shopper", is_bundle=False)
    color = ColorFactory()
    BOM.objects.create(
        product=product,
        material=felt,
        quantity_per_unit="0.60",
        unit=BOM.Unit.SQUARE_METER,
    )
    BOM.objects.create(
        product=product,
        material=leather,
        quantity_per_unit="0.20",
        unit=BOM.Unit.SQUARE_METER,
    )
    sales_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Тест",
    )
    line = SalesOrderLine.objects.create(
        sales_order=sales_order,
        product=product,
        variant=Variant.objects.create(product=product, color=color),
        quantity=3,
    )

    requirements = calculate_material_requirements_for_sales_order_line(line=line)
    by_name = {item.material_name: item for item in requirements}

    assert by_name["Felt"].quantity == Decimal("1.80")
    assert by_name["Leather smooth"].quantity == Decimal("0.60")
    assert by_name["Felt"].unit == BOM.Unit.SQUARE_METER


@pytest.mark.django_db
def test_calculate_material_requirements_for_bundle_line():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    bundle = ProductFactory(name="Set", is_bundle=True)
    clutch = ProductFactory(name="Clutch", is_bundle=False)
    strap = ProductFactory(name="Strap", is_bundle=False)
    color = ColorFactory()
    BundleComponent.objects.create(bundle=bundle, component=clutch, quantity=1, is_primary=True)
    BundleComponent.objects.create(bundle=bundle, component=strap, quantity=2, is_primary=False)
    BOM.objects.create(
        product=clutch,
        material=felt,
        quantity_per_unit="0.25",
        unit=BOM.Unit.SQUARE_METER,
    )
    BOM.objects.create(
        product=strap,
        material=leather,
        quantity_per_unit="1.00",
        unit=BOM.Unit.PIECE,
    )
    sales_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Опт",
    )
    line = SalesOrderLine.objects.create(
        sales_order=sales_order,
        product=bundle,
        variant=Variant.objects.create(product=bundle, color=color),
        quantity=2,
    )

    requirements = calculate_material_requirements_for_sales_order_line(line=line)
    by_name = {item.material_name: item for item in requirements}

    assert by_name["Felt"].quantity == Decimal("0.50")
    assert by_name["Leather smooth"].quantity == Decimal("4.00")
    assert by_name["Leather smooth"].unit == BOM.Unit.PIECE
