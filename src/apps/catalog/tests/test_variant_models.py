"""Tests for Variant model constraints."""
import pytest
from django.db import IntegrityError

from apps.catalog.models import Variant
from apps.materials.models import Material, MaterialColor

from .conftest import ColorFactory, ProductFactory


@pytest.mark.django_db
def test_variant_unique_per_dimensions():
    product = ProductFactory()
    color = ColorFactory()

    Variant.objects.create(product=product, color=color)

    with pytest.raises(IntegrityError):
        Variant.objects.create(product=product, color=color)


@pytest.mark.django_db
def test_variant_requires_color_or_primary_material_color():
    product = ProductFactory()

    with pytest.raises(IntegrityError):
        Variant.objects.create(product=product)


@pytest.mark.django_db
def test_variant_requires_primary_when_secondary_color_set():
    product = ProductFactory()
    material = Material.objects.create(name="Felt")
    secondary = MaterialColor.objects.create(material=material, name="Black", code=101)

    with pytest.raises(IntegrityError):
        Variant.objects.create(
            product=product,
            secondary_material_color=secondary,
        )


@pytest.mark.django_db
def test_variant_disallows_mix_of_color_and_primary_material_color():
    product = ProductFactory()
    color = ColorFactory()
    material = Material.objects.create(name="Leather")
    primary = MaterialColor.objects.create(material=material, name="Blue", code=202)

    with pytest.raises(IntegrityError):
        Variant.objects.create(
            product=product,
            color=color,
            primary_material_color=primary,
        )
