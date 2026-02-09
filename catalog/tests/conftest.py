"""Fixtures for catalog tests."""

import factory
from catalog.models import Color, ProductModel
from factory.django import DjangoModelFactory


class ProductModelFactory(DjangoModelFactory):
    class Meta:
        model = ProductModel

    name = factory.Sequence(lambda n: f"Model {n}")


class ColorFactory(DjangoModelFactory):
    class Meta:
        model = Color

    name = factory.Sequence(lambda n: f"Color {n}")
    code = factory.Sequence(lambda n: n + 100)
    availability_status = "in_stock"
