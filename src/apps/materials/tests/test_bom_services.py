"""Tests for product material requirements service."""
from decimal import Decimal

import pytest

from apps.catalog.models import BundleComponent
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.customer_orders.models import CustomerOrder, CustomerOrderLine
from apps.materials.models import Material, ProductMaterial
from apps.materials.services import calculate_material_requirements_for_customer_order_line


@pytest.mark.django_db
def test_calculate_material_requirements_for_single_product_line():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    product = ProductModelFactory(name="Shopper", is_bundle=False)
    color = ColorFactory()
    ProductMaterial.objects.create(
        product_model=product,
        material=felt,
        quantity_per_unit="0.60",
        unit=ProductMaterial.Unit.SQUARE_METER,
    )
    ProductMaterial.objects.create(
        product_model=product,
        material=leather,
        quantity_per_unit="0.20",
        unit=ProductMaterial.Unit.SQUARE_METER,
    )
    customer_order = CustomerOrder.objects.create(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="ТОВ Тест",
    )
    line = CustomerOrderLine.objects.create(
        customer_order=customer_order,
        product_model=product,
        color=color,
        quantity=3,
    )

    requirements = calculate_material_requirements_for_customer_order_line(line=line)
    by_name = {item.material_name: item for item in requirements}

    assert by_name["Felt"].quantity == Decimal("1.80")
    assert by_name["Leather smooth"].quantity == Decimal("0.60")
    assert by_name["Felt"].unit == ProductMaterial.Unit.SQUARE_METER


@pytest.mark.django_db
def test_calculate_material_requirements_for_bundle_line():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    bundle = ProductModelFactory(name="Set", is_bundle=True)
    clutch = ProductModelFactory(name="Clutch", is_bundle=False)
    strap = ProductModelFactory(name="Strap", is_bundle=False)
    color = ColorFactory()
    BundleComponent.objects.create(bundle=bundle, component=clutch, quantity=1, is_primary=True)
    BundleComponent.objects.create(bundle=bundle, component=strap, quantity=2, is_primary=False)
    ProductMaterial.objects.create(
        product_model=clutch,
        material=felt,
        quantity_per_unit="0.25",
        unit=ProductMaterial.Unit.SQUARE_METER,
    )
    ProductMaterial.objects.create(
        product_model=strap,
        material=leather,
        quantity_per_unit="1.00",
        unit=ProductMaterial.Unit.PIECE,
    )
    customer_order = CustomerOrder.objects.create(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="ТОВ Опт",
    )
    line = CustomerOrderLine.objects.create(
        customer_order=customer_order,
        product_model=bundle,
        color=color,
        quantity=2,
    )

    requirements = calculate_material_requirements_for_customer_order_line(line=line)
    by_name = {item.material_name: item for item in requirements}

    assert by_name["Felt"].quantity == Decimal("0.50")
    assert by_name["Leather smooth"].quantity == Decimal("4.00")
    assert by_name["Leather smooth"].unit == ProductMaterial.Unit.PIECE
