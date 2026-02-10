"""HTTP layer and view tests for materials."""

import pytest
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_materials_views_require_authentication(client):
    from apps.materials.models import Material

    material = Material.objects.create(name="Cotton")
    assert client.get(reverse("materials")).status_code == 302
    assert client.get(reverse("material_edit", kwargs={"pk": material.pk})).status_code == 302


@pytest.mark.django_db(transaction=True)
def test_materials_list_hides_archived_by_default(client):
    from apps.materials.models import Material
    from apps.accounts.models import User

    user = User.objects.create_user(username="materials_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Material.objects.create(name="Active material")
    Material.objects.create(name="Archived material", archived_at=timezone.now())

    response = client.get(reverse("materials"))
    assert response.status_code == 200
    assert b"Active material" in response.content
    assert b"Archived material" not in response.content
    assert b'class="catalog-chip-link catalog-chip-availability-in"' in response.content
    assert reverse("materials_archive").encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_materials_create_and_archive_unarchive(client):
    from apps.materials.models import Material
    from apps.accounts.models import User

    user = User.objects.create_user(username="materials_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    create_response = client.post(reverse("materials"), data={"name": "Linen"})
    assert create_response.status_code == 302
    material = Material.objects.get(name="Linen")
    assert material.archived_at is None

    archive_response = client.post(reverse("material_archive", kwargs={"pk": material.pk}))
    assert archive_response.status_code == 302
    assert archive_response.url == reverse("material_edit", kwargs={"pk": material.pk})
    material.refresh_from_db()
    assert material.archived_at is not None

    unarchive_response = client.post(reverse("material_unarchive", kwargs={"pk": material.pk}))
    assert unarchive_response.status_code == 302
    assert unarchive_response.url == reverse("material_edit", kwargs={"pk": material.pk})
    material.refresh_from_db()
    assert material.archived_at is None


@pytest.mark.django_db(transaction=True)
def test_materials_archive_page_shows_only_archived(client):
    from apps.materials.models import Material
    from apps.accounts.models import User

    user = User.objects.create_user(username="materials_archive_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    Material.objects.create(name="Active material")
    Material.objects.create(name="Archived material", archived_at=timezone.now())

    response = client.get(reverse("materials_archive"))
    assert response.status_code == 200
    assert b"Archived material" in response.content
    assert b"Active material" not in response.content
