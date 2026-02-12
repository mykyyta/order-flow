"""Catalog model and view tests."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Color, Product


def test_product_str():
    product = Product(name="Test")
    assert "Test" in str(product)


def test_color_str():
    c = Color(name="Red", code=1)
    assert "Red" in str(c)


@pytest.mark.django_db
def test_products_views_require_authentication(client):
    assert client.get(reverse("products")).status_code == 302


@pytest.mark.django_db(transaction=True)
def test_catalog_lists_hide_archived_by_default(client):
    from apps.accounts.models import User

    user = User.objects.create_user(username="catalog_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Product.objects.create(name="Active model")
    Product.objects.create(name="Archived model", archived_at=timezone.now())

    models_response = client.get(reverse("products"))
    assert models_response.status_code == 200
    assert b"Active model" in models_response.content
    assert b"Archived model" not in models_response.content
    assert b'class="catalog-chip-link catalog-chip-availability-in"' in models_response.content
    assert reverse("products_archive").encode() in models_response.content


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

