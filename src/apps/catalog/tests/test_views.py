"""Catalog model and view tests."""
import pytest
from django.urls import reverse

from apps.catalog.models import Color, ProductModel

from .conftest import ColorFactory


def test_product_model_str():
    pm = ProductModel(name="Test")
    assert "Test" in str(pm)


def test_color_str():
    c = Color(name="Red", code=1)
    assert "Red" in str(c)


@pytest.mark.django_db
def test_models_and_colors_views_require_authentication(client):
    color = ColorFactory()
    assert client.get(reverse("product_models")).status_code == 302
    assert client.get(reverse("colors")).status_code == 302
    assert client.get(reverse("color_edit", kwargs={"pk": color.pk})).status_code == 302


@pytest.mark.django_db(transaction=True)
def test_color_edit_redirects_to_colors_list(client):
    from apps.orders.models import CustomUser
    user = CustomUser.objects.create_user(username="color_editor", password="pass12345")
    color = ColorFactory(name="Ivory", code=101)
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    response = client.post(
        reverse("color_edit", kwargs={"pk": color.pk}),
        data={
            "name": "ivory",
            "code": 101,
            "availability_status": "low_stock",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("colors")
    color.refresh_from_db()
    assert color.availability_status == "low_stock"
