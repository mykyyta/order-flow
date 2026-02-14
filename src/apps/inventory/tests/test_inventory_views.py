import pytest
from django.urls import reverse

from apps.accounts.tests.conftest import UserFactory
from apps.catalog.tests.conftest import ProductFactory
from apps.inventory.models import ProductStock
from apps.materials.models import Material, MaterialColor, MaterialStock
from apps.warehouses.services import get_default_warehouse


AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.mark.django_db(transaction=True)
def test_inventory_materials_list_renders_stock_records(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    mat = Material.objects.create(name="Leather", stock_unit="m2")
    color = MaterialColor.objects.create(material=mat, name="Black", code=1)
    MaterialStock.objects.create(
        warehouse=warehouse,
        material=mat,
        material_color=color,
        unit="m2",
        quantity="2.000",
    )

    response = client.get(reverse("inventory_materials"))
    assert response.status_code == 200
    assert mat.name.encode() in response.content
    assert color.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_inventory_materials_adjustment_add_creates_stock(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    mat = Material.objects.create(name="Felt", stock_unit="m")
    color = MaterialColor.objects.create(material=mat, name="Blue", code=11)

    response = client.post(
        reverse("inventory_materials_add"),
        data={
            "material": str(mat.id),
            "material_color": str(color.id),
            "quantity": "3.5",
        },
    )
    assert response.status_code == 302

    record = MaterialStock.objects.get(
        warehouse=warehouse,
        material=mat,
        material_color=color,
        unit="m",
    )
    assert str(record.quantity) == "3.500"


@pytest.mark.django_db(transaction=True)
def test_inventory_products_adjustment_add_creates_stock(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    get_default_warehouse()

    product = ProductFactory(kind="standard")
    # Production UI uses material colors; keep the same for inventory.
    primary = Material.objects.create(name="Primary", stock_unit="pcs")
    product.primary_material = primary
    product.save(update_fields=["primary_material"])
    color = MaterialColor.objects.create(material=primary, name="Red", code=3)

    response = client.post(
        reverse("inventory_products_add"),
        data={
            "product": str(product.id),
            "primary_material_color": str(color.id),
            "secondary_material_color": "",
            "quantity": "4",
            "notes": "init",
        },
    )
    assert response.status_code == 302

    product_list = client.get(reverse("inventory_products"))
    assert product_list.status_code == 200
    assert product.name.encode() in product_list.content


@pytest.mark.django_db(transaction=True)
def test_inventory_products_adjustment_add_allows_uncolored_component(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    product = ProductFactory(kind="component", primary_material=None, secondary_material=None)

    response = client.post(
        reverse("inventory_products_add"),
        data={
            "product": str(product.id),
            "primary_material_color": "",
            "secondary_material_color": "",
            "quantity": "2",
            "notes": "",
        },
    )
    assert response.status_code == 302

    stock = ProductStock.objects.select_related("variant").get(warehouse=warehouse)
    assert stock.variant.product_id == product.id
    assert stock.variant.color_id is None
    assert stock.variant.primary_material_color_id is None
    assert stock.variant.secondary_material_color_id is None
    assert stock.quantity == 2


@pytest.mark.django_db(transaction=True)
def test_inventory_products_adjustment_add_blocks_bundles(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    bundle = ProductFactory(kind="bundle")
    response = client.post(
        reverse("inventory_products_add"),
        data={
            "product": str(bundle.id),
            "primary_material_color": "",
            "secondary_material_color": "",
            "quantity": "1",
            "notes": "",
        },
    )
    assert response.status_code == 200
    assert ProductStock.objects.filter(warehouse=warehouse).count() == 0


@pytest.mark.django_db(transaction=True)
def test_inventory_material_stock_detail_renders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    mat = Material.objects.create(name="Leather", stock_unit="m2")
    record = MaterialStock.objects.create(
        warehouse=warehouse,
        material=mat,
        material_color=None,
        unit="m2",
        quantity="2.000",
    )

    response = client.get(reverse("inventory_material_stock_detail", kwargs={"pk": record.id}))
    assert response.status_code == 200
    assert mat.name.encode() in response.content
    assert "Рухи".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_inventory_product_stock_detail_renders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    product = ProductFactory(kind="standard")
    from apps.catalog.models import Variant

    variant = Variant.objects.create(product=product)
    record = ProductStock.objects.create(
        warehouse=warehouse,
        variant=variant,
        quantity=1,
    )

    response = client.get(reverse("inventory_product_stock_detail", kwargs={"pk": record.id}))
    assert response.status_code == 200
    assert product.name.encode() in response.content
    assert "Рухи".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_inventory_materials_writeoff_creates_movement(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    mat = Material.objects.create(name="Glue", stock_unit="ml")
    stock = MaterialStock.objects.create(
        warehouse=warehouse,
        material=mat,
        material_color=None,
        unit="ml",
        quantity="2.000",
    )

    response = client.post(
        reverse("inventory_materials_writeoff"),
        data={
            "material": str(mat.id),
            "material_color": "",
            "quantity": "1.000",
        },
    )
    assert response.status_code == 302

    stock.refresh_from_db()
    assert str(stock.quantity) == "1.000"


@pytest.mark.django_db(transaction=True)
def test_inventory_products_writeoff_creates_movement(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    product = ProductFactory(kind="standard")
    from apps.catalog.models import Variant

    variant = Variant.objects.create(product=product)
    stock = ProductStock.objects.create(warehouse=warehouse, variant=variant, quantity=3)

    response = client.post(
        reverse("inventory_products_writeoff"),
        data={
            "product": str(product.id),
            "primary_material_color": "",
            "secondary_material_color": "",
            "quantity": "2",
            "notes": "",
        },
    )
    assert response.status_code == 302
    stock.refresh_from_db()
    assert stock.quantity == 1
