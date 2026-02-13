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


@pytest.mark.django_db(transaction=True)
def test_product_detail_shows_material_fields_and_bom_section(client):
    from apps.accounts.models import User
    from apps.materials.models import Material

    user = User.objects.create_user(username="model_detail_viewer", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Wallet")
    Material.objects.create(name="Leather")

    response = client.get(reverse("product_edit", kwargs={"pk": product.pk}))
    assert response.status_code == 200
    assert b'name="primary_material"' not in response.content
    assert b'name="secondary_material"' not in response.content
    assert "Матеріали моделі".encode() in response.content
    assert "Норми матеріалів".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_product_detail_primary_secondary_set_via_product_material_roles(client):
    from apps.accounts.models import User
    from apps.materials.models import Material
    from apps.catalog.models import ProductMaterial

    user = User.objects.create_user(username="model_detail_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    primary = Material.objects.create(name="Leather")
    secondary = Material.objects.create(name="Felt")
    product = Product.objects.create(name="Clutch")

    r1 = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={
            "material": str(primary.pk),
            "role": ProductMaterial.Role.PRIMARY,
            "notes": "",
        },
    )
    assert r1.status_code == 302
    pm_primary = ProductMaterial.objects.get(product=product, material=primary)
    assert pm_primary.role == ProductMaterial.Role.PRIMARY

    r2 = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={
            "material": str(secondary.pk),
            "role": ProductMaterial.Role.SECONDARY,
            "notes": "",
        },
    )
    assert r2.status_code == 302

    product.refresh_from_db()
    assert product.primary_material_id == primary.pk
    assert product.secondary_material_id == secondary.pk
    assert ProductMaterial.objects.filter(
        product=product, material=primary, role=ProductMaterial.Role.PRIMARY
    ).exists()
    assert ProductMaterial.objects.filter(
        product=product, material=secondary, role=ProductMaterial.Role.SECONDARY
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_product_material_add_creates_link(client):
    from apps.accounts.models import User
    from apps.catalog.models import ProductMaterial
    from apps.materials.models import Material

    user = User.objects.create_user(username="model_material_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Bag")
    material = Material.objects.create(name="Thread")

    response = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={
            "material": str(material.pk),
            "role": ProductMaterial.Role.OTHER,
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert ProductMaterial.objects.filter(product=product, material=material).exists()


@pytest.mark.django_db(transaction=True)
def test_product_material_primary_role_is_unique_per_product(client):
    from apps.accounts.models import User
    from apps.catalog.models import ProductMaterial
    from apps.materials.models import Material

    user = User.objects.create_user(username="pm_primary_unique", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Model X")
    m1 = Material.objects.create(name="Leather")
    m2 = Material.objects.create(name="Felt")

    r1 = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m1.pk), "role": ProductMaterial.Role.PRIMARY, "notes": ""},
    )
    assert r1.status_code == 302
    product.refresh_from_db()
    assert product.primary_material_id == m1.pk

    r2 = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m2.pk), "role": ProductMaterial.Role.PRIMARY, "notes": ""},
    )
    assert r2.status_code == 302
    product.refresh_from_db()
    assert product.primary_material_id == m2.pk
    assert ProductMaterial.objects.get(product=product, material=m2).role == ProductMaterial.Role.PRIMARY
    assert ProductMaterial.objects.get(product=product, material=m1).role == ProductMaterial.Role.OTHER


@pytest.mark.django_db(transaction=True)
def test_product_material_secondary_requires_primary(client):
    from apps.accounts.models import User
    from apps.catalog.models import ProductMaterial
    from apps.materials.models import Material

    user = User.objects.create_user(username="pm_secondary_requires_primary", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Model Y", primary_material=None)
    m = Material.objects.create(name="Thread")

    response = client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m.pk), "role": ProductMaterial.Role.SECONDARY, "notes": ""},
    )
    assert response.status_code == 200
    assert "Спочатку обери основний матеріал.".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_product_detail_primary_change_updates_product_material_roles(client):
    from apps.accounts.models import User
    from apps.catalog.models import ProductMaterial
    from apps.materials.models import Material

    user = User.objects.create_user(username="product_primary_change", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    m1 = Material.objects.create(name="Leather")
    m2 = Material.objects.create(name="Felt")
    product = Product.objects.create(name="Clutch")

    client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m1.pk), "role": ProductMaterial.Role.PRIMARY, "notes": ""},
    )
    assert ProductMaterial.objects.get(product=product, material=m1).role == ProductMaterial.Role.PRIMARY

    client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m2.pk), "role": ProductMaterial.Role.PRIMARY, "notes": ""},
    )
    product.refresh_from_db()
    assert product.primary_material_id == m2.pk
    assert ProductMaterial.objects.get(product=product, material=m2).role == ProductMaterial.Role.PRIMARY
    assert ProductMaterial.objects.get(product=product, material=m1).role == ProductMaterial.Role.OTHER


@pytest.mark.django_db(transaction=True)
def test_product_bom_add_creates_norm(client):
    from apps.accounts.models import User
    from apps.materials.models import BOM, Material

    user = User.objects.create_user(username="model_bom_editor", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Bag")
    material = Material.objects.create(name="Thread")

    response = client.post(
        reverse("product_bom_add", kwargs={"pk": product.pk}),
        data={
            "material": str(material.pk),
            "quantity_per_unit": "1.000",
            "unit": BOM.Unit.PIECE,
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert BOM.objects.filter(product=product, material=material).exists()


@pytest.mark.django_db(transaction=True)
def test_product_material_delete_removes_only_other_role(client):
    from apps.accounts.models import User
    from apps.catalog.models import ProductMaterial
    from apps.materials.models import Material

    user = User.objects.create_user(username="pm_delete", password="pass12345")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    product = Product.objects.create(name="Bag")
    m1 = Material.objects.create(name="Leather")
    m2 = Material.objects.create(name="Thread")

    client.post(
        reverse("product_material_add", kwargs={"pk": product.pk}),
        data={"material": str(m1.pk), "role": ProductMaterial.Role.PRIMARY},
    )
    pm1 = ProductMaterial.objects.get(product=product, material=m1)

    client.post(reverse("product_material_add", kwargs={"pk": product.pk}), data={"material": str(m2.pk)})
    pm2 = ProductMaterial.objects.get(product=product, material=m2)

    # Cannot delete primary
    r1 = client.post(reverse("product_material_delete", kwargs={"pk": product.pk, "pm_pk": pm1.pk}))
    assert r1.status_code == 302
    assert ProductMaterial.objects.filter(pk=pm1.pk).exists()

    # Can delete other
    r2 = client.post(reverse("product_material_delete", kwargs={"pk": product.pk, "pm_pk": pm2.pk}))
    assert r2.status_code == 302
    assert not ProductMaterial.objects.filter(pk=pm2.pk).exists()
