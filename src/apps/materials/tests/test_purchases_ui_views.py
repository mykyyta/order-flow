from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.tests.conftest import UserFactory
from apps.materials.models import (
    Material,
    MaterialColor,
    MaterialStock,
    SupplierMaterialOffer,
    MaterialUnit,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
)
from apps.warehouses.services import get_default_warehouse


AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.mark.django_db(transaction=True)
def test_purchases_list_renders_purchase_orders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop UI")
    PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)

    response = client.get(reverse("purchases"))
    assert response.status_code == 200
    assert response.context["show_page_header"] is False
    assert supplier.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_detail_renders_lines_and_receive_link(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop Detail")
    material = Material.objects.create(name="Leather", stock_unit=MaterialUnit.PIECE)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("10.00"),
    )

    response = client.get(reverse("purchase_detail", kwargs={"pk": po.pk}))
    assert response.status_code == 200
    assert material.name.encode() in response.content
    assert reverse("purchase_line_receive", kwargs={"pk": po.pk, "line_pk": line.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_line_receive_adds_stock(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    supplier = Supplier.objects.create(name="Shop Receive")
    material = Material.objects.create(name="Thread", stock_unit=MaterialUnit.PIECE)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.SENT, created_by=user)
    line = PurchaseOrderLine.objects.create(
        purchase_order=po,
        material=material,
        quantity=Decimal("5.000"),
        unit=MaterialUnit.PIECE,
        unit_price=Decimal("1.00"),
    )

    response = client.post(
        reverse("purchase_line_receive", kwargs={"pk": po.pk, "line_pk": line.pk}),
        data={"quantity": "2.000", "notes": "ok"},
    )
    assert response.status_code == 302

    stock = MaterialStock.objects.get(warehouse=warehouse, material=material, unit=MaterialUnit.PIECE)
    assert stock.quantity == Decimal("2.000")


@pytest.mark.django_db(transaction=True)
def test_purchase_add_step1_renders_supplier_only(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    Supplier.objects.create(name="Shop Wizard")

    response = client.get(reverse("purchase_add"))
    assert response.status_code == 200
    assert "Постачальник".encode() in response.content
    assert "Трек/ТТН".encode() not in response.content
    assert "Очікується".encode() not in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_add_step1_creates_draft_and_redirects_to_step2(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop Wizard Create")

    response = client.post(reverse("purchase_add"), data={"supplier": supplier.pk})
    assert response.status_code == 302

    po = PurchaseOrder.objects.get()
    assert po.supplier_id == supplier.pk
    assert po.status == PurchaseOrder.Status.DRAFT
    assert response["Location"] == reverse("purchase_add_lines", kwargs={"pk": po.pk})


@pytest.mark.django_db(transaction=True)
def test_purchase_add_lines_step2_adds_line_and_redirects_back(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop Wizard Lines")
    material = Material.objects.create(name="Clasp", stock_unit=MaterialUnit.PIECE)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)

    response = client.get(reverse("purchase_add_lines", kwargs={"pk": po.pk}))
    assert response.status_code == 200

    next_url = reverse("purchase_add_lines", kwargs={"pk": po.pk})
    response = client.post(
        f"{reverse('purchase_line_add', kwargs={'pk': po.pk})}?next={next_url}",
        data={"material": material.pk, "quantity": "2.000", "unit_price": "10.00"},
    )
    assert response.status_code == 302
    assert response["Location"] == next_url

    line = PurchaseOrderLine.objects.get(purchase_order=po)
    assert line.unit == material.stock_unit


@pytest.mark.django_db(transaction=True)
def test_purchase_requests_list_renders_requests(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Needle", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user, notes="Need stuff")
    PurchaseRequestLine.objects.create(request=pr, material=material)

    response = client.get(reverse("purchase_requests"))
    assert response.status_code == 200
    assert response.context["show_page_header"] is False
    assert material.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_request_edit_renders_and_updates(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Hook", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user, notes="Need hooks")
    PurchaseRequestLine.objects.create(
        request=pr,
        material=material,
        requested_quantity=Decimal("2.000"),
        unit=MaterialUnit.PIECE,
    )
    line = pr.lines.get()

    response = client.get(reverse("purchase_request_detail", kwargs={"pk": pr.pk}))
    assert response.status_code == 200
    assert "Статус".encode() in response.content
    assert "Коментар".encode() in response.content
    assert reverse("purchase_request_line_order", kwargs={"line_pk": line.pk}).encode() in response.content

    response = client.post(
        reverse("purchase_request_detail", kwargs={"pk": pr.pk}),
        data={"status": PurchaseRequest.Status.DONE, "requested_quantity": "3.000", "notes": "Closed"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("purchase_requests")
    pr.refresh_from_db()
    line.refresh_from_db()
    assert pr.status == PurchaseRequest.Status.DONE
    assert pr.notes == "Closed"
    assert line.requested_quantity == Decimal("3.000")


@pytest.mark.django_db(transaction=True)
def test_purchase_requests_list_search_filters_by_material_and_color(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()

    material = Material.objects.create(name="Felt", stock_unit=MaterialUnit.SQUARE_METER)
    color = MaterialColor.objects.create(material=material, name="Green", code=2)

    pr1 = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user, notes="")
    PurchaseRequestLine.objects.create(request=pr1, material=material, material_color=color)

    pr2 = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user, notes="")
    other = Material.objects.create(name="Thread", stock_unit=MaterialUnit.PIECE)
    PurchaseRequestLine.objects.create(request=pr2, material=other)

    response = client.get(reverse("purchase_requests") + "?q=felt")
    assert response.status_code == 200
    assert f"Редагувати заявку #{pr1.id}".encode() in response.content
    assert f"Редагувати заявку #{pr2.id}".encode() not in response.content

    response = client.get(reverse("purchase_requests") + "?q=green")
    assert response.status_code == 200
    assert f"Редагувати заявку #{pr1.id}".encode() in response.content
    assert f"Редагувати заявку #{pr2.id}".encode() not in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_request_create_for_material_hides_color_field_when_no_colors(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    material = Material.objects.create(name="NoColor Felt", stock_unit=MaterialUnit.SQUARE_METER)

    response = client.get(reverse("purchase_request_add_for_material", kwargs={"material_pk": material.pk}))
    assert response.status_code == 200
    assert "Колір".encode() not in response.content
    assert material.get_stock_unit_display().encode() in response.content
    assert b"placeholder" in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_request_create_for_material_requires_color_when_material_has_colors(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    material = Material.objects.create(name="Color Felt", stock_unit=MaterialUnit.SQUARE_METER)
    MaterialColor.objects.create(material=material, name="Red", code=1)

    response = client.post(
        reverse("purchase_request_add_for_material", kwargs={"material_pk": material.pk}),
        data={"material_color": "", "requested_quantity": "", "notes": ""},
    )
    assert response.status_code == 200
    assert "Обери колір".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_request_set_status_done_closes_open_lines(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Glue", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user)
    line = pr.lines.create(material=material, status="open")

    response = client.post(
        reverse("purchase_request_set_status", kwargs={"pk": pr.pk}),
        data={"status": "done"},
    )
    assert response.status_code == 302

    pr.refresh_from_db()
    line.refresh_from_db()
    assert pr.status == "done"
    assert line.status == "done"


@pytest.mark.django_db(transaction=True)
def test_purchase_request_set_status_cancelled_cancels_open_lines(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Rivets", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user)
    line = pr.lines.create(material=material, status="open")

    response = client.post(
        reverse("purchase_request_set_status", kwargs={"pk": pr.pk}),
        data={"status": "cancelled"},
    )
    assert response.status_code == 302

    pr.refresh_from_db()
    line.refresh_from_db()
    assert pr.status == "cancelled"
    assert line.status == "cancelled"


@pytest.mark.django_db(transaction=True)
def test_purchase_request_line_set_status_done_auto_closes_request_when_all_lines_closed(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    material = Material.objects.create(name="Buckles", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user)
    line = pr.lines.create(material=material, status="open")

    response = client.post(
        reverse("purchase_request_line_set_status", kwargs={"line_pk": line.pk}),
        data={"status": "done"},
    )
    assert response.status_code == 302
    pr.refresh_from_db()
    assert pr.status == "done"


@pytest.mark.django_db(transaction=True)
def test_purchase_pick_request_line_for_order_renders_and_contains_prefilled_order_link(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    warehouse = get_default_warehouse()
    supplier = Supplier.objects.create(name="Shop Pick")
    material = Material.objects.create(name="Zipper", stock_unit=MaterialUnit.PIECE)

    pr = PurchaseRequest.objects.create(warehouse=warehouse, created_by=user)
    line = pr.lines.create(material=material, requested_quantity=Decimal("3.000"), unit=MaterialUnit.PIECE)
    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)

    response = client.get(reverse("purchase_pick_request_line_for_order", kwargs={"pk": po.pk}))
    assert response.status_code == 200
    order_url = (
        reverse("purchase_request_line_order", kwargs={"line_pk": line.pk})
        + f"?supplier={supplier.pk}&purchase_order={po.pk}"
    )
    assert order_url.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_detail_shows_add_from_request_button(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Shop Add From PR")
    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)

    response = client.get(reverse("purchase_detail", kwargs={"pk": po.pk}))
    assert response.status_code == 200
    assert reverse("purchase_line_add_choose", kwargs={"pk": po.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_suppliers_list_renders_suppliers(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Supplier UI List")
    material = Material.objects.create(name="Supplier UI Material", stock_unit=MaterialUnit.PIECE)
    SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=MaterialUnit.PIECE,
    )

    response = client.get(reverse("suppliers"))
    assert response.status_code == 200
    assert response.context["show_page_header"] is False
    assert supplier.name.encode() in response.content
    assert material.name.encode() in response.content
    assert reverse("supplier_detail", kwargs={"pk": supplier.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_supplier_offers_list_renders_offers(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Supplier List")
    material = Material.objects.create(name="Offer Material List", stock_unit=MaterialUnit.PIECE)
    offer = SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=MaterialUnit.PIECE,
        title="Offer For List",
    )

    response = client.get(reverse("supplier_offers"))
    assert response.status_code == 200
    assert response.context["show_page_header"] is False
    assert supplier.name.encode() in response.content
    assert material.name.encode() in response.content
    assert offer.title.encode() in response.content
    assert reverse("supplier_offer_start").encode() in response.content
    assert reverse("supplier_offer_detail", kwargs={"pk": offer.pk}).encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_supplier_detail_renders_and_purchase_create_creates_order(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Supplier Detail Page")

    response = client.get(reverse("supplier_detail", kwargs={"pk": supplier.pk}))
    assert response.status_code == 200
    assert supplier.name.encode() in response.content

    response = client.post(reverse("supplier_purchase_create", kwargs={"pk": supplier.pk}))
    assert response.status_code == 302
    po = PurchaseOrder.objects.get()
    assert po.supplier_id == supplier.pk


@pytest.mark.django_db(transaction=True)
def test_supplier_offer_detail_renders_and_updates(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Detail Supplier")
    material = Material.objects.create(name="Offer Detail Material", stock_unit=MaterialUnit.PIECE)
    offer = SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=MaterialUnit.PIECE,
        title="Offer Detail Title",
    )

    response = client.get(
        reverse("supplier_offer_detail", kwargs={"pk": offer.pk}) + f"?next={reverse('supplier_offers')}"
    )
    assert response.status_code == 200
    assert offer.title.encode() in response.content
    assert material.name.encode() in response.content

    response = client.post(
        reverse("supplier_offer_detail", kwargs={"pk": offer.pk}) + f"?next={reverse('supplier_offers')}",
        data={
            "supplier": supplier.pk,
            "material_color": "",
            "title": "Offer Detail Title Updated",
            "sku": "",
            "url": "",
            "price_per_unit": "",
            "notes": "",
            "next": reverse("supplier_offers"),
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("supplier_offers")
    offer.refresh_from_db()
    assert offer.title == "Offer Detail Title Updated"


@pytest.mark.django_db(transaction=True)
def test_supplier_offer_start_redirects_to_material_offer_add_with_prefill(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Start Supplier")
    material = Material.objects.create(name="Offer Start Material", stock_unit=MaterialUnit.PIECE)

    response = client.post(reverse("supplier_offer_start"), data={"supplier": supplier.pk, "material": material.pk})
    assert response.status_code == 302
    assert reverse("supplier_offer_add", kwargs={"material_pk": material.pk}).encode() in response["Location"].encode()
    assert f"supplier={supplier.pk}".encode() in response["Location"].encode()


@pytest.mark.django_db(transaction=True)
def test_supplier_add_creates_and_redirects_to_suppliers(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    response = client.post(reverse("supplier_add"), data={"name": "New Supplier"})
    assert response.status_code == 302
    assert Supplier.objects.filter(name="New Supplier").exists()


@pytest.mark.django_db(transaction=True)
def test_supplier_add_with_next_purchase_add_redirects_with_supplier_prefilled(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    next_url = reverse("purchase_add")
    response = client.post(f"{reverse('supplier_add')}?next={next_url}", data={"name": "Wizard Supplier"})
    assert response.status_code == 302

    created = Supplier.objects.get(name="Wizard Supplier")
    assert response["Location"] == f"{next_url}?supplier={created.pk}"


@pytest.mark.django_db(transaction=True)
def test_purchase_start_material_renders_materials(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    material = Material.objects.create(name="Material Start", stock_unit=MaterialUnit.PIECE)

    response = client.get(reverse("purchase_start_material"))
    assert response.status_code == 200
    assert response.context["show_page_header"] is False
    assert material.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_start_material_offers_renders_offers(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Supplier")
    material = Material.objects.create(name="Offer Material", stock_unit=MaterialUnit.PIECE)
    offer = SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=MaterialUnit.PIECE,
        title="Offer Title",
        sku="SKU-1",
        url="https://example.com/item",
        price_per_unit=Decimal("12.34"),
    )

    response = client.get(reverse("purchase_start_material_offers", kwargs={"material_pk": material.pk}))
    assert response.status_code == 200
    assert supplier.name.encode() in response.content
    assert offer.title.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_add_from_offer_creates_purchase_order_and_line(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Create Supplier")
    material = Material.objects.create(name="Offer Create Material", stock_unit=MaterialUnit.PIECE)
    offer = SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=MaterialUnit.PIECE,
        title="Offer Create Title",
        price_per_unit=Decimal("9.99"),
    )

    response = client.post(
        reverse("purchase_add_from_offer", kwargs={"offer_pk": offer.pk}),
        data={"quantity": "2.000"},
    )
    assert response.status_code == 302

    po = PurchaseOrder.objects.get()
    line = PurchaseOrderLine.objects.get(purchase_order=po)
    assert po.supplier_id == supplier.pk
    assert line.material_id == material.pk
    assert line.supplier_offer_id == offer.pk
    assert line.unit_price == Decimal("9.99")


@pytest.mark.django_db(transaction=True)
def test_supplier_offer_add_creates_offer_and_redirects_back_to_offers(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Add Supplier")
    material = Material.objects.create(name="Offer Add Material", stock_unit=MaterialUnit.PIECE)

    response = client.post(
        reverse("supplier_offer_add", kwargs={"material_pk": material.pk}),
        data={"supplier": supplier.pk, "title": "New Offer", "url": "https://example.com/new"},
    )
    assert response.status_code == 302
    assert SupplierMaterialOffer.objects.filter(material=material, supplier=supplier, title="New Offer").exists()


@pytest.mark.django_db(transaction=True)
def test_purchase_add_lines_requires_color_when_material_has_colors(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Color Required Supplier")
    material = Material.objects.create(name="Color Required Material", stock_unit=MaterialUnit.PIECE)
    MaterialColor.objects.create(material=material, name="Black", code=1)

    po = PurchaseOrder.objects.create(supplier=supplier, status=PurchaseOrder.Status.DRAFT, created_by=user)
    response = client.post(
        reverse("purchase_line_add", kwargs={"pk": po.pk}),
        data={"material": material.pk, "material_color": "", "quantity": "1.000", "unit_price": ""},
    )
    assert response.status_code == 200
    assert PurchaseOrderLine.objects.filter(purchase_order=po).count() == 0
    assert "Обери колір".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_supplier_offer_add_requires_color_when_material_has_colors(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Color Required Supplier")
    material = Material.objects.create(name="Offer Color Required Material", stock_unit=MaterialUnit.PIECE)
    MaterialColor.objects.create(material=material, name="Blue", code=2)

    response = client.post(
        reverse("supplier_offer_add", kwargs={"material_pk": material.pk}),
        data={"supplier": supplier.pk, "material_color": "", "title": "Offer Without Color"},
    )
    assert response.status_code == 200
    assert SupplierMaterialOffer.objects.filter(title="Offer Without Color").count() == 0
    assert "Обери колір".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_purchase_add_from_offer_blocks_uncolored_offer_for_colored_material(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    supplier = Supplier.objects.create(name="Offer Uncolored Supplier")
    material = Material.objects.create(name="Offer Uncolored Material", stock_unit=MaterialUnit.PIECE)
    MaterialColor.objects.create(material=material, name="Red", code=3)
    offer = SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        material_color=None,
        unit=MaterialUnit.PIECE,
        title="Bad Offer",
    )

    response = client.post(
        reverse("purchase_add_from_offer", kwargs={"offer_pk": offer.pk}),
        data={"quantity": "1.000"},
    )
    assert response.status_code == 302
    assert PurchaseOrder.objects.count() == 0
