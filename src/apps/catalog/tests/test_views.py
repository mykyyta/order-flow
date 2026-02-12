"""Catalog model and view tests."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Color, Product

from .conftest import ColorFactory


def test_product_str():
    product = Product(name="Test")
    assert "Test" in str(product)


def test_color_str():
    c = Color(name="Red", code=1)
    assert "Red" in str(c)


@pytest.mark.django_db
def test_models_and_colors_views_require_authentication(client):
    color = ColorFactory()
    assert client.get(reverse("products")).status_code == 302
    assert client.get(reverse("colors")).status_code == 302
    assert client.get(reverse("color_edit", kwargs={"pk": color.pk})).status_code == 302


@pytest.mark.django_db(transaction=True)
def test_color_edit_redirects_to_colors_list(client):
    from apps.accounts.models import User
    user = User.objects.create_user(username="color_editor", password="pass12345")
    color = ColorFactory(name="Ivory", code=101)
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    response = client.post(
        reverse("color_edit", kwargs={"pk": color.pk}),
        data={
            "name": "ivory",
            "code": 101,
            "status": "low_stock",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("colors")
    color.refresh_from_db()
    assert color.status == "low_stock"


@pytest.mark.django_db(transaction=True)
def test_catalog_lists_hide_archived_by_default(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="catalog_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Product.objects.create(name="Active model")
    Product.objects.create(name="Archived model", archived_at=timezone.now())

    Color.objects.create(name="Active color", code=111)
    Color.objects.create(name="Archived color", code=222, archived_at=timezone.now())

    models_response = client.get(reverse("products"))
    assert models_response.status_code == 200
    assert b"Active model" in models_response.content
    assert b"Archived model" not in models_response.content
    assert b'class="catalog-chip-link catalog-chip-availability-in"' in models_response.content
    assert reverse("products_archive").encode() in models_response.content

    colors_response = client.get(reverse("colors"))
    assert colors_response.status_code == 200
    assert b"Active color" in colors_response.content
    assert b"Archived color" not in colors_response.content
    assert reverse("colors_archive").encode() in colors_response.content


@pytest.mark.django_db(transaction=True)
def test_product_edit_page_exists(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="model_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    model = Product.objects.create(name="Wallet")
    response = client.get(reverse("product_edit", kwargs={"pk": model.pk}))
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_product_archive_and_unarchive(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="model_archiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    model = Product.objects.create(name="Clutch")

    archive_response = client.post(reverse("product_archive", kwargs={"pk": model.pk}))
    assert archive_response.status_code == 302
    assert archive_response.url == reverse("product_edit", kwargs={"pk": model.pk})
    model.refresh_from_db()
    assert model.archived_at is not None

    unarchive_response = client.post(reverse("product_unarchive", kwargs={"pk": model.pk}))
    assert unarchive_response.status_code == 302
    assert unarchive_response.url == reverse("product_edit", kwargs={"pk": model.pk})
    model.refresh_from_db()
    assert model.archived_at is None


@pytest.mark.django_db(transaction=True)
def test_color_archive_and_unarchive(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_archiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    color = Color.objects.create(name="Blue", code=777, status="in_stock")

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


@pytest.mark.django_db(transaction=True)
def test_models_archive_page_shows_only_archived(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="models_archive_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Product.objects.create(name="Active model")
    Product.objects.create(name="Archived model", archived_at=timezone.now())

    response = client.get(reverse("products_archive"))
    assert response.status_code == 200
    assert b"Archived model" in response.content
    assert b"Active model" not in response.content


@pytest.mark.django_db(transaction=True)
def test_colors_archive_page_shows_only_archived(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="colors_archive_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Color.objects.create(name="Active color", code=500)
    Color.objects.create(name="Archived color", code=600, archived_at=timezone.now())

    response = client.get(reverse("colors_archive"))
    assert response.status_code == 200
    assert b"Archived color" in response.content
    assert b"Active color" not in response.content
