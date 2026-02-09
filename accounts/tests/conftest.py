"""Fixtures for accounts tests."""

import factory
from factory.django import DjangoModelFactory
from orders.models import CustomUser


class UserFactory(DjangoModelFactory):
    class Meta:
        model = CustomUser

    username = factory.Sequence(lambda n: f"user_{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
