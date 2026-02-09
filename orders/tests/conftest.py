"""Shared fixtures and factories for orders tests."""

import factory
import pytest
from catalog.models import Color, ProductModel
from factory.django import DjangoModelFactory
from orders.models import CustomUser, Order


class UserFactory(DjangoModelFactory):
    class Meta:
        model = CustomUser

    username = factory.Sequence(lambda n: f"user_{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


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


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    model = factory.SubFactory(ProductModelFactory)
    color = factory.SubFactory(ColorFactory)
    current_status = "new"


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def order(db):
    return OrderFactory()
