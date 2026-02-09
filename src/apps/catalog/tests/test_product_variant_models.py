"""Tests for ProductVariant model constraints."""
import pytest
from django.db import IntegrityError

from apps.catalog.models import ProductVariant
from apps.materials.models import Material, MaterialColor

from .conftest import ColorFactory, ProductModelFactory


@pytest.mark.django_db
def test_product_variant_unique_per_variant_dimensions():
    product = ProductModelFactory()
    color = ColorFactory()

    ProductVariant.objects.create(product=product, color=color)

    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(product=product, color=color)


@pytest.mark.django_db
def test_product_variant_requires_color_or_primary_material_color():
    product = ProductModelFactory()

    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(product=product)


@pytest.mark.django_db
def test_product_variant_requires_primary_when_secondary_color_set():
    product = ProductModelFactory()
    material = Material.objects.create(name="Felt")
    secondary = MaterialColor.objects.create(material=material, name="Black", code=101)

    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(
            product=product,
            secondary_material_color=secondary,
        )


@pytest.mark.django_db
def test_product_variant_disallows_mix_of_color_and_primary_material_color():
    product = ProductModelFactory()
    color = ColorFactory()
    material = Material.objects.create(name="Leather")
    primary = MaterialColor.objects.create(material=material, name="Blue", code=202)

    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(
            product=product,
            color=color,
            primary_material_color=primary,
        )
