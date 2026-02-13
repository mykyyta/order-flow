"""Fixtures for catalog tests."""
import factory
from factory.django import DjangoModelFactory

from apps.catalog.models import Color, Product


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Model {n}")
    kind = Product.Kind.STANDARD


class ColorFactory(DjangoModelFactory):
    class Meta:
        model = Color

    name = factory.Sequence(lambda n: f"Color {n}")
    code = factory.Sequence(lambda n: n + 100)
    status = "in_stock"
