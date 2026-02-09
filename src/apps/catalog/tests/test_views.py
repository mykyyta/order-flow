"""Catalog model and view tests."""
import pytest
from django.urls import reverse
from django.utils import timezone

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


@pytest.mark.django_db(transaction=True)
def test_catalog_lists_hide_archived_by_default(client):
    from apps.orders.models import CustomUser

    user = CustomUser.objects.create_user(username="catalog_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    ProductModel.objects.create(name="Active model")
    ProductModel.objects.create(name="Archived model", archived_at=timezone.now())

    Color.objects.create(name="Active color", code=111)
    Color.objects.create(name="Archived color", code=222, archived_at=timezone.now())

    models_response = client.get(reverse("product_models"))
    assert models_response.status_code == 200
    assert b"Active model" in models_response.content
    assert b"Archived model" not in models_response.content
    assert b'class="catalog-chip-link catalog-chip-availability-in"' in models_response.content

    colors_response = client.get(reverse("colors"))
    assert colors_response.status_code == 200
    assert b"Active color" in colors_response.content
    assert b"Archived color" not in colors_response.content


@pytest.mark.django_db(transaction=True)
def test_product_model_edit_page_exists(client):
    from apps.orders.models import CustomUser

    user = CustomUser.objects.create_user(username="model_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    model = ProductModel.objects.create(name="Wallet")
    response = client.get(reverse("product_model_edit", kwargs={"pk": model.pk}))
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_product_model_archive_and_unarchive(client):
    from apps.orders.models import CustomUser

    user = CustomUser.objects.create_user(username="model_archiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    model = ProductModel.objects.create(name="Clutch")

    archive_response = client.post(reverse("product_model_archive", kwargs={"pk": model.pk}))
    assert archive_response.status_code == 302
    assert archive_response.url == reverse("product_model_edit", kwargs={"pk": model.pk})
    model.refresh_from_db()
    assert model.archived_at is not None

    unarchive_response = client.post(reverse("product_model_unarchive", kwargs={"pk": model.pk}))
    assert unarchive_response.status_code == 302
    assert unarchive_response.url == reverse("product_model_edit", kwargs={"pk": model.pk})
    model.refresh_from_db()
    assert model.archived_at is None


@pytest.mark.django_db(transaction=True)
def test_color_archive_and_unarchive(client):
    from apps.orders.models import CustomUser

    user = CustomUser.objects.create_user(username="color_archiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    color = Color.objects.create(name="Blue", code=777, availability_status="in_stock")

    archive_response = client.post(reverse("color_archive", kwargs={"pk": color.pk}))
    assert archive_response.status_code == 302
    assert archive_response.url == reverse("color_edit", kwargs={"pk": color.pk})
    color.refresh_from_db()
    assert color.archived_at is not None

    unarchive_response = client.post(reverse("color_unarchive", kwargs={"pk": color.pk}))
    assert unarchive_response.status_code == 302
    assert unarchive_response.url == reverse("color_edit", kwargs={"pk": color.pk})
    color.refresh_from_db()
    assert color.archived_at is None
