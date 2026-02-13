"""Model tests for materials domain."""
import pytest
from django.db import IntegrityError

from apps.catalog.tests.conftest import ProductFactory
from apps.catalog.models import ProductMaterial
from apps.materials.models import Material, MaterialColor


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
    product = ProductFactory(name="Mini bag")

    ProductMaterial.objects.create(
        product=product,
        material=felt,
    )

    with pytest.raises(IntegrityError):
        ProductMaterial.objects.create(
            product=product,
            material=felt,
        )


@pytest.mark.django_db
def test_product_material_str():
    felt = Material.objects.create(name="Felt")
    product = ProductFactory(name="Maxi bag")
    item = ProductMaterial.objects.create(
        product=product,
        material=felt,
    )
    assert str(item) == "Maxi bag: Felt (Інший)"
