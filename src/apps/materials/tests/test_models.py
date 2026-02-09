"""Model tests for materials domain."""
import pytest
from django.db import IntegrityError

from apps.catalog.tests.conftest import ProductModelFactory
from apps.materials.models import Material, MaterialColor, ProductMaterial


@pytest.mark.django_db
def test_material_color_unique_per_material_name():
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather")

    MaterialColor.objects.create(material=felt, name="Black", code=101)
    MaterialColor.objects.create(material=leather, name="Black", code=101)

    with pytest.raises(IntegrityError):
        MaterialColor.objects.create(material=felt, name="Black", code=102)


@pytest.mark.django_db
def test_material_color_str():
    felt = Material.objects.create(name="Felt")
    color = MaterialColor.objects.create(material=felt, name="Blue", code=201)
    assert str(color) == "Felt: Blue"


@pytest.mark.django_db
def test_product_material_unique_per_product_material():
    felt = Material.objects.create(name="Felt")
    product = ProductModelFactory(name="Mini bag")

    ProductMaterial.objects.create(
        product_model=product,
        material=felt,
        quantity_per_unit="0.35",
        unit=ProductMaterial.Unit.SQUARE_METER,
    )

    with pytest.raises(IntegrityError):
        ProductMaterial.objects.create(
            product_model=product,
            material=felt,
            quantity_per_unit="0.40",
            unit=ProductMaterial.Unit.SQUARE_METER,
        )


@pytest.mark.django_db
def test_product_material_str():
    felt = Material.objects.create(name="Felt")
    product = ProductModelFactory(name="Maxi bag")
    item = ProductMaterial.objects.create(
        product_model=product,
        material=felt,
        quantity_per_unit="0.50",
        unit=ProductMaterial.Unit.SQUARE_METER,
    )
    assert str(item) == "Maxi bag: Felt 0.50 m2"
