"""Tests for customer order services."""
import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import BundleColorMapping, BundleComponent
from apps.catalog.models import BundlePreset, BundlePresetComponent
from apps.catalog.models import ProductVariant
from apps.customer_orders.models import (
    CustomerOrder,
    CustomerOrderLine,
    CustomerOrderLineComponent,
)
from apps.customer_orders.services import create_customer_order
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.materials.models import Material, MaterialColor



@pytest.mark.django_db
def test_create_customer_order_creates_plain_line():
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()

    order = create_customer_order(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="ТОВ Тест",
        lines_data=[
            {
                "product_model_id": model.id,
                "color_id": color.id,
                "quantity": 3,
            }
        ],
    )

    line = CustomerOrderLine.objects.get(customer_order=order)
    assert line.product_model_id == model.id
    assert line.color_id == color.id
    assert line.product_variant is not None
    assert line.product_variant.product_id == model.id
    assert line.product_variant.color_id == color.id
    assert line.quantity == 3
    assert line.production_mode == CustomerOrderLine.ProductionMode.AUTO
    assert line.production_status == CustomerOrderLine.ProductionStatus.PENDING


@pytest.mark.django_db
def test_create_customer_order_expands_fixed_bundle_mapping():
    bundle = ProductModelFactory(is_bundle=True)
    clutch = ProductModelFactory(is_bundle=False)
    strap = ProductModelFactory(is_bundle=False)
    total_black = ColorFactory(name="Total black")
    black = ColorFactory(name="Black")

    BundleComponent.objects.create(bundle=bundle, component=clutch, quantity=1, is_primary=True)
    BundleComponent.objects.create(bundle=bundle, component=strap, quantity=1, is_primary=False)

    BundleColorMapping.objects.create(
        bundle=bundle,
        bundle_color=total_black,
        component=clutch,
        component_color=black,
    )
    BundleColorMapping.objects.create(
        bundle=bundle,
        bundle_color=total_black,
        component=strap,
        component_color=black,
    )

    order = create_customer_order(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="ФОП Іваненко",
        lines_data=[
            {
                "product_model_id": bundle.id,
                "color_id": total_black.id,
                "quantity": 2,
            }
        ],
    )

    line = CustomerOrderLine.objects.get(customer_order=order)
    components = CustomerOrderLineComponent.objects.filter(order_line=line).order_by("component_id")

    assert components.count() == 2
    assert list(components.values_list("component_id", flat=True)) == sorted([clutch.id, strap.id])
    assert set(components.values_list("color_id", flat=True)) == {black.id}
    assert not components.filter(product_variant__isnull=True).exists()


@pytest.mark.django_db
def test_create_customer_order_saves_custom_bundle_components():
    bundle = ProductModelFactory(is_bundle=True)
    clutch = ProductModelFactory(is_bundle=False)
    strap = ProductModelFactory(is_bundle=False)
    blue = ColorFactory(name="Blue")
    black = ColorFactory(name="Black")

    BundleComponent.objects.create(bundle=bundle, component=clutch, quantity=1, is_primary=True)
    BundleComponent.objects.create(bundle=bundle, component=strap, quantity=2, is_primary=False)

    order = create_customer_order(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="TOB Blue",
        lines_data=[
            {
                "product_model_id": bundle.id,
                "color_id": None,
                "quantity": 1,
                "component_colors": [
                    {"component_id": clutch.id, "color_id": blue.id},
                    {"component_id": strap.id, "color_id": black.id},
                ],
                "production_mode": CustomerOrderLine.ProductionMode.FORCE,
            }
        ],
    )

    line = CustomerOrderLine.objects.get(customer_order=order)
    components = CustomerOrderLineComponent.objects.filter(order_line=line).order_by("component_id")

    assert line.color_id is None
    assert line.production_mode == CustomerOrderLine.ProductionMode.FORCE
    assert components.count() == 2
    assert list(components.values_list("component_id", "color_id")) == [
        (clutch.id, blue.id),
        (strap.id, black.id),
    ]


@pytest.mark.django_db
def test_create_customer_order_requires_component_colors_for_custom_bundle():
    bundle = ProductModelFactory(is_bundle=True)

    with pytest.raises(ValueError, match="component colors"):
        create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="No components",
            lines_data=[
                {
                    "product_model_id": bundle.id,
                    "color_id": None,
                    "quantity": 1,
                }
            ],
        )


@pytest.mark.django_db
def test_create_customer_order_saves_primary_and_secondary_material_colors():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    blue_felt = MaterialColor.objects.create(material=felt, name="Blue", code=13)
    black_leather = MaterialColor.objects.create(material=leather, name="Black", code=2)
    product = ProductModelFactory(
        is_bundle=False,
        primary_material=felt,
        secondary_material=leather,
    )

    order = create_customer_order(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="ТОВ Тест",
        lines_data=[
            {
                "product_model_id": product.id,
                "quantity": 1,
                "primary_material_color_id": blue_felt.id,
                "secondary_material_color_id": black_leather.id,
            }
        ],
    )

    line = order.lines.get()
    assert line.primary_material_color == blue_felt
    assert line.secondary_material_color == black_leather


@pytest.mark.django_db
def test_create_customer_order_rejects_primary_color_from_wrong_material():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    wrong_color = MaterialColor.objects.create(material=leather, name="Brown", code=9)
    product = ProductModelFactory(is_bundle=False, primary_material=felt)

    with pytest.raises(ValueError, match="primary material"):
        create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="ТОВ Тест",
            lines_data=[
                {
                    "product_model_id": product.id,
                    "quantity": 1,
                    "primary_material_color_id": wrong_color.id,
                }
            ],
        )


@pytest.mark.django_db
def test_create_customer_order_expands_bundle_preset_components():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    black_felt = MaterialColor.objects.create(material=felt, name="Black", code=101)
    black_leather = MaterialColor.objects.create(material=leather, name="Black", code=1)
    bundle = ProductModelFactory(is_bundle=True)
    clutch = ProductModelFactory(is_bundle=False, primary_material=felt)
    strap = ProductModelFactory(is_bundle=False, primary_material=leather)
    BundleComponent.objects.create(bundle=bundle, component=clutch, quantity=1, is_primary=True)
    BundleComponent.objects.create(bundle=bundle, component=strap, quantity=1, is_primary=False)
    preset = BundlePreset.objects.create(bundle=bundle, name="Total black")
    BundlePresetComponent.objects.create(
        preset=preset,
        component=clutch,
        primary_material_color=black_felt,
    )
    BundlePresetComponent.objects.create(
        preset=preset,
        component=strap,
        primary_material_color=black_leather,
    )

    order = create_customer_order(
        source=CustomerOrder.Source.WHOLESALE,
        customer_info="Preset test",
        lines_data=[
            {
                "product_model_id": bundle.id,
                "quantity": 1,
                "bundle_preset_id": preset.id,
            }
        ],
    )

    line = order.lines.get()
    components = list(line.component_colors.order_by("component_id"))
    assert len(components) == 2
    assert components[0].primary_material_color is not None
    assert components[1].primary_material_color is not None


@pytest.mark.django_db
def test_customer_order_line_rejects_mismatched_product_variant_on_save():
    customer_order = CustomerOrder.objects.create(
        source=CustomerOrder.Source.SITE,
        customer_info="Mismatch line",
    )
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    wrong_variant = ProductVariant.objects.create(
        product=model,
        color=ColorFactory(),
    )

    with pytest.raises(ValidationError, match="must match"):
        CustomerOrderLine.objects.create(
            customer_order=customer_order,
            product_model=model,
            color=color,
            product_variant=wrong_variant,
            quantity=1,
        )


@pytest.mark.django_db
def test_customer_order_component_rejects_mismatched_product_variant_on_save():
    customer_order = CustomerOrder.objects.create(
        source=CustomerOrder.Source.SITE,
        customer_info="Mismatch component",
    )
    bundle = ProductModelFactory(is_bundle=True)
    component = ProductModelFactory(is_bundle=False)
    line = CustomerOrderLine.objects.create(
        customer_order=customer_order,
        product_model=bundle,
        color=ColorFactory(),
    )
    component_color = ColorFactory()
    wrong_variant = ProductVariant.objects.create(
        product=ProductModelFactory(is_bundle=False),
        color=component_color,
    )

    with pytest.raises(ValidationError, match="must match"):
        CustomerOrderLineComponent.objects.create(
            order_line=line,
            component=component,
            color=component_color,
            product_variant=wrong_variant,
        )
