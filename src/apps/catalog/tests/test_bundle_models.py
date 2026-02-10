"""Tests for bundle-related catalog models."""
import pytest
from django.db import IntegrityError

from apps.catalog.models import (
    BundleColorMapping,
    BundleComponent,
    BundlePreset,
    BundlePresetComponent,
)
from apps.materials.models import Material, MaterialColor

from .conftest import ColorFactory, ProductModelFactory


@pytest.mark.django_db
def test_product_model_is_bundle_defaults_to_false():
    product_model = ProductModelFactory()
    assert product_model.is_bundle is False


@pytest.mark.django_db
def test_bundle_component_unique_per_bundle_component_pair():
    bundle = ProductModelFactory(is_bundle=True)
    component = ProductModelFactory(is_bundle=False)

    BundleComponent.objects.create(
        bundle=bundle,
        component=component,
        quantity=1,
        is_primary=True,
    )

    with pytest.raises(IntegrityError):
        BundleComponent.objects.create(
            bundle=bundle,
            component=component,
            quantity=2,
            is_primary=False,
        )


@pytest.mark.django_db
def test_bundle_component_has_required_flag_and_optional_group():
    bundle = ProductModelFactory(is_bundle=True)
    component = ProductModelFactory(is_bundle=False)

    relation = BundleComponent.objects.create(
        bundle=bundle,
        component=component,
        quantity=1,
        is_primary=False,
    )

    assert relation.is_required is True
    assert relation.group == ""


@pytest.mark.django_db
def test_bundle_color_mapping_unique_per_bundle_color_component():
    bundle = ProductModelFactory(is_bundle=True)
    component = ProductModelFactory(is_bundle=False)
    bundle_color = ColorFactory()
    component_color = ColorFactory()

    BundleColorMapping.objects.create(
        bundle=bundle,
        bundle_color=bundle_color,
        component=component,
        component_color=component_color,
    )

    with pytest.raises(IntegrityError):
        BundleColorMapping.objects.create(
            bundle=bundle,
            bundle_color=bundle_color,
            component=component,
            component_color=ColorFactory(),
        )


@pytest.mark.django_db
def test_product_model_supports_primary_and_secondary_materials():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")

    product = ProductModelFactory(
        is_bundle=False,
        primary_material=felt,
        secondary_material=leather,
    )

    assert product.primary_material == felt
    assert product.secondary_material == leather


@pytest.mark.django_db
def test_bundle_preset_component_unique_per_component():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather")
    black_felt = MaterialColor.objects.create(material=felt, name="Black", code=1)
    black_leather = MaterialColor.objects.create(material=leather, name="Black", code=1)
    bundle = ProductModelFactory(is_bundle=True)
    component = ProductModelFactory(is_bundle=False)
    preset = BundlePreset.objects.create(bundle=bundle, name="Total black")

    BundlePresetComponent.objects.create(
        preset=preset,
        component=component,
        primary_material_color=black_felt,
        secondary_material_color=black_leather,
    )
    with pytest.raises(IntegrityError):
        BundlePresetComponent.objects.create(
            preset=preset,
            component=component,
            primary_material_color=black_felt,
            secondary_material_color=black_leather,
        )
