"""Shared fixtures and factories for orders tests."""
import pytest
import factory
from factory.django import DjangoModelFactory

from apps.catalog.models import Color, ProductModel
from apps.orders.models import CustomUser, Order


class UserFactory(DjangoModelFactory):
    class Meta:
        model = CustomUser
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        password = extracted or "testpass123"
        obj.set_password(password)
        if create:
            obj.save(update_fields=["password"])


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
