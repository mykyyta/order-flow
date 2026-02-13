"""HTTP layer and view tests for materials."""

import pytest
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_materials_views_require_authentication(client):
    from apps.materials.models import Material

    material = Material.objects.create(name="Cotton")
    assert client.get(reverse("materials")).status_code == 302
    assert client.get(reverse("material_detail", kwargs={"pk": material.pk})).status_code == 302


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
    assert archive_response.url == reverse("material_detail", kwargs={"pk": material.pk})
    material.refresh_from_db()
    assert material.archived_at is not None

    unarchive_response = client.post(reverse("material_unarchive", kwargs={"pk": material.pk}))
    assert unarchive_response.status_code == 302
    assert unarchive_response.url == reverse("material_detail", kwargs={"pk": material.pk})
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


@pytest.mark.django_db(transaction=True)
def test_material_detail_shows_colors(client):
    from apps.materials.models import Material, MaterialColor
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    material = Material.objects.create(name="Leather")
    MaterialColor.objects.create(material=material, code=1, name="Black")
    MaterialColor.objects.create(material=material, code=2, name="Brown")
    MaterialColor.objects.create(
        material=material, code=99, name="Archived color", archived_at=timezone.now()
    )

    response = client.get(reverse("material_detail", kwargs={"pk": material.pk}))
    assert response.status_code == 200
    assert b"Black" in response.content
    assert b"Brown" in response.content
    assert b"Archived color" not in response.content
    assert reverse("material_colors_archive", kwargs={"pk": material.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_material_color_add_and_edit(client):
    from apps.materials.models import Material, MaterialColor
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    material = Material.objects.create(name="Fabric")

    # Add color
    add_url = reverse("material_color_add", kwargs={"pk": material.pk})
    response = client.post(add_url, data={"code": 1, "name": "red"})
    assert response.status_code == 302
    color = MaterialColor.objects.get(material=material, code=1)
    assert color.name == "Red"  # capitalized

    # Edit color
    edit_url = reverse("material_color_edit", kwargs={"pk": material.pk, "color_pk": color.pk})
    response = client.post(edit_url, data={"code": 1, "name": "crimson"})
    assert response.status_code == 302
    color.refresh_from_db()
    assert color.name == "Crimson"


@pytest.mark.django_db(transaction=True)
def test_material_color_archive(client):
    from apps.materials.models import Material, MaterialColor
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_archiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    material = Material.objects.create(name="Silk")
    color = MaterialColor.objects.create(material=material, code=1, name="White")
    assert color.archived_at is None

    archive_url = reverse(
        "material_color_archive", kwargs={"pk": material.pk, "color_pk": color.pk}
    )
    response = client.post(archive_url)
    assert response.status_code == 302
    color.refresh_from_db()
    assert color.archived_at is not None


@pytest.mark.django_db(transaction=True)
def test_material_colors_archive_page_shows_archived_only(client):
    from apps.materials.models import Material, MaterialColor
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_archive_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    material = Material.objects.create(name="Canvas")
    MaterialColor.objects.create(material=material, code=1, name="Active White")
    archived = MaterialColor.objects.create(
        material=material, code=2, name="Archived Black", archived_at=timezone.now()
    )

    response = client.get(reverse("material_colors_archive", kwargs={"pk": material.pk}))
    assert response.status_code == 200
    assert b"Archived Black" in response.content
    assert b"Active White" not in response.content
    assert reverse(
        "material_color_unarchive", kwargs={"pk": material.pk, "color_pk": archived.pk}
    ).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_material_color_unarchive(client):
    from apps.materials.models import Material, MaterialColor
    from apps.accounts.models import User

    user = User.objects.create_user(username="color_unarchiver", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    material = Material.objects.create(name="Wool")
    color = MaterialColor.objects.create(
        material=material, code=7, name="Grey", archived_at=timezone.now()
    )

    unarchive_url = reverse(
        "material_color_unarchive", kwargs={"pk": material.pk, "color_pk": color.pk}
    )
    response = client.post(unarchive_url)
    assert response.status_code == 302
    assert response.url == reverse("material_colors_archive", kwargs={"pk": material.pk})

    color.refresh_from_db()
    assert color.archived_at is None
