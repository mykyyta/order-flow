"""HTTP layer and view tests for orders."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.production.domain.status import STATUS_BLOCKED, STATUS_DONE, STATUS_NEW

from .conftest import ColorFactory, OrderFactory, ProductFactory, UserFactory

AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.mark.django_db(transaction=True)
def test_transition_map_present_in_page(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.get(reverse("orders_active"))
    assert response.status_code == 200
    assert b"transition-map-data" in response.content
    assert b"bulk-status-form" in response.content
    assert b"clear-selection-btn" in response.content


@pytest.mark.django_db(transaction=True)
def test_active_orders_render_comment_marker(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    OrderFactory(
        product=model,
        color=color,
        comment="ready for review",
        status=STATUS_NEW,
    )
    response = client.get(reverse("orders_active"))
    assert response.status_code == 200
    assert b"data-has-comment=\"1\"" in response.content
    assert b"data-order-comment" in response.content


@pytest.mark.django_db(transaction=True)
def test_current_orders_list_is_paginated_and_excludes_finished(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    for _ in range(51):
        OrderFactory(product=model, color=color, status=STATUS_NEW)
    OrderFactory(product=model, color=color, status=STATUS_DONE)
    response = client.get(reverse("orders_active"))
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 51
    assert len(response.context["orders"]) == 50
    assert response.context["page_obj"].has_next()
    second_page = client.get(reverse("orders_active"), {"page": 2})
    assert second_page.status_code == 200
    assert len(second_page.context["orders"]) == 1
    assert not second_page.context["page_obj"].has_next()


@pytest.mark.django_db(transaction=True)
def test_current_orders_supports_status_filter(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    target = OrderFactory(
        product=model,
        color=color,
        comment="vip batch",
        status=STATUS_BLOCKED,
    )
    OrderFactory(
        product=model,
        color=color,
        comment="regular batch",
        status=STATUS_NEW,
    )
    response = client.get(reverse("orders_active"), {"filter": STATUS_BLOCKED})
    assert response.status_code == 200
    orders = list(response.context["orders"])
    assert len(orders) == 1
    assert orders[0].id == target.id


@pytest.mark.django_db(transaction=True)
def test_finished_orders_search_filters_across_all_finished(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory(name="Model History")
    color = ColorFactory(name="Navy", code=7)
    target = OrderFactory(
        product=model,
        color=color,
        comment="special archive order",
        status=STATUS_DONE,
    )
    OrderFactory(
        product=model,
        color=color,
        comment="other archive order",
        status=STATUS_DONE,
    )
    OrderFactory(
        product=model,
        color=color,
        comment="special archive order",
        status=STATUS_NEW,
    )
    response = client.get(reverse("orders_completed"), {"q": "special"})
    assert response.status_code == 200
    orders = list(response.context["page_obj"].object_list)
    assert len(orders) == 1
    assert orders[0].id == target.id


@pytest.mark.django_db(transaction=True)
def test_finished_orders_search_preserves_query_params_for_pagination(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    for _ in range(21):
        OrderFactory(
            product=model,
            color=color,
            comment="archive",
            status=STATUS_DONE,
        )
    response = client.get(reverse("orders_completed"), {"q": "archive"})
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 21
    assert len(response.context["page_obj"].object_list) == 20
    assert b"?page=2&q=archive" in response.content or b"page=2" in response.content
    second_page = client.get(reverse("orders_completed"), {"q": "archive", "page": 2})
    assert second_page.status_code == 200
    assert len(second_page.context["page_obj"].object_list) == 1


@pytest.mark.django_db(transaction=True)
def test_order_detail_renders_status_indicator(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    order = OrderFactory(product=model, color=color, status=STATUS_BLOCKED)
    response = client.get(reverse("order_detail", kwargs={"pk": order.id}))
    assert response.status_code == 200
    assert b"text-orange-500" in response.content
    assert order.get_status_display().encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_orders_create_hides_archived_catalog_items(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    active_model = ProductFactory(name="Active model")
    archived_model = ProductFactory(name="Archived model", archived_at=timezone.now())
    active_color = ColorFactory(name="Active color", code=1001)
    archived_color = ColorFactory(
        name="Archived color",
        code=2002,
        archived_at=timezone.now(),
    )

    response = client.get(reverse("orders_create"))
    assert response.status_code == 200
    assert active_model.name.encode() in response.content
    assert archived_model.name.encode() not in response.content
    assert active_color.name.encode() in response.content
    assert archived_color.name.encode() not in response.content


@pytest.mark.django_db(transaction=True)
def test_order_edit_includes_archived_model_and_color_in_dropdown(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    model = ProductFactory(name="Model to archive")
    color = ColorFactory(name="Color to archive", code=888)
    order = OrderFactory(product=model, color=color, status=STATUS_NEW)

    model.archived_at = timezone.now()
    model.save(update_fields=["archived_at"])
    color.archived_at = timezone.now()
    color.save(update_fields=["archived_at"])

    response = client.get(reverse("order_edit", kwargs={"pk": order.id}))
    assert response.status_code == 200
    assert model.name.encode() in response.content
    assert color.name.encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_order_edit_allows_saving_when_product_primary_material_changed(client):
    """Changing Product.primary_material should not brick editing old orders."""
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    order = OrderFactory(comment="before")
    product = order.product
    old_color = order.variant.primary_material_color

    from apps.materials.models import Material

    product.primary_material = Material.objects.create(name="New primary material")
    product.save(update_fields=["primary_material"])

    response = client.post(
        reverse("order_edit", kwargs={"pk": order.id}),
        data={
            "product": str(product.pk),
            "primary_material_color": str(old_color.pk),
            "comment": "after",
        },
    )
    assert response.status_code == 302
    order.refresh_from_db()
    assert order.comment == "after"


@pytest.mark.django_db(transaction=True)
def test_order_edit_disables_primary_color_when_product_primary_changed(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    order = OrderFactory()
    product = order.product

    from apps.materials.models import Material

    product.primary_material = Material.objects.create(name="Other primary")
    product.save(update_fields=["primary_material"])

    response = client.get(reverse("order_edit", kwargs={"pk": order.id}))
    assert response.status_code == 200
    assert b'name="primary_material_color"' in response.content
    assert b"disabled" in response.content


def test_message_alert_class_mapping():
    from apps.ui.templatetags.order_ui import message_alert_class
    assert message_alert_class("error") == "alert alert-error"
    assert message_alert_class("success") == "alert alert-success"
    assert message_alert_class("warning extra") == "alert alert-warning"
    assert message_alert_class("unknown") == "alert alert-info"


@pytest.mark.django_db(transaction=True)
def test_palette_lab_renders_page(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    response = client.get(reverse("palette_lab"))
    assert response.status_code == 200
    assert b"orders/palette_lab.html" in response.templates[0].origin.name.encode()


@pytest.mark.django_db(transaction=True)
def test_orders_bulk_status_updates_multiple_orders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    order1 = OrderFactory(product=model, color=color, status=STATUS_NEW)
    order2 = OrderFactory(product=model, color=color, status=STATUS_NEW)

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [order1.id, order2.id], "new_status": "in_progress"},
    )
    assert response.status_code == 302
    order1.refresh_from_db()
    order2.refresh_from_db()
    assert order1.status == "in_progress"
    assert order2.status == "in_progress"


@pytest.mark.django_db(transaction=True)
def test_orders_bulk_status_empty_selection_shows_error(client):
    """Empty orders selection causes form validation error."""
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [], "new_status": "in_progress"},
        follow=True,
    )
    assert response.status_code == 200
    messages_list = list(response.context["messages"])
    # Form validation fails with generic error
    assert any("упс" in str(m).lower() for m in messages_list)


@pytest.mark.django_db(transaction=True)
def test_orders_bulk_status_no_status_shows_error(client):
    """Empty status causes form validation error."""
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    order = OrderFactory(product=model, color=color, status=STATUS_NEW)

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [order.id], "new_status": ""},
        follow=True,
    )
    assert response.status_code == 200
    messages_list = list(response.context["messages"])
    # Form validation fails with generic error
    assert any("упс" in str(m).lower() for m in messages_list)


@pytest.mark.django_db(transaction=True)
def test_orders_bulk_status_invalid_transition_shows_error(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory()
    color = ColorFactory()
    # Order with status "in_progress" cannot transition back to "new"
    order = OrderFactory(product=model, color=color, status="in_progress")

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [order.id], "new_status": "new"},
        follow=True,
    )
    assert response.status_code == 200
    messages_list = list(response.context["messages"])
    assert any("не можна" in str(m).lower() for m in messages_list)


@pytest.mark.django_db(transaction=True)
def test_orders_create_post_creates_order(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    color = ColorFactory()
    model = ProductFactory(primary_material=color.material)

    response = client.post(
        reverse("orders_create"),
        data={
            "product": model.id,
            "primary_material_color": color.id,
            "is_etsy": False,
            "is_embroidery": False,
            "is_urgent": False,
            "comment": "Test order",
        },
    )
    assert response.status_code == 302

    from apps.production.models import ProductionOrder

    order = ProductionOrder.objects.get(comment="Test order")
    assert order.product == model
    assert order.variant.primary_material_color == color
    assert order.status == STATUS_NEW


@pytest.mark.django_db(transaction=True)
def test_orders_create_post_without_color_shows_form_error(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    color = ColorFactory()
    model = ProductFactory(primary_material=color.material)

    response = client.post(
        reverse("orders_create"),
        data={
            "product": model.id,
            "primary_material_color": "",
            "is_etsy": False,
            "is_embroidery": False,
            "is_urgent": False,
            "comment": "No color order",
        },
    )

    assert response.status_code == 200
    assert "Обери основний колір".encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_orders_create_post_without_primary_color_is_allowed_for_model_without_primary_material(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductFactory(primary_material=None)

    response = client.post(
        reverse("orders_create"),
        data={
            "product": model.id,
            "primary_material_color": "",
            "is_etsy": False,
            "is_embroidery": False,
            "is_urgent": False,
            "comment": "No primary material",
        },
    )

    assert response.status_code == 302


@pytest.mark.django_db(transaction=True)
def test_orders_create_post_for_bundle_creates_component_orders(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    from apps.catalog.models import BundleComponent
    from apps.materials.models import Material

    bag_material = Material.objects.create(name="Bag material")
    strap_material = Material.objects.create(name="Strap material")
    bag_color = ColorFactory(material=bag_material, name="Bag color", code=1111)
    strap_color = ColorFactory(material=strap_material, name="Strap color", code=2222)

    bag = ProductFactory(
        name="Bag",
        primary_material=bag_material,
        kind="standard",
        allows_embroidery=False,
    )
    strap = ProductFactory(
        name="Strap",
        primary_material=strap_material,
        kind="component",
        allows_embroidery=True,
    )
    bundle = ProductFactory(name="Bag + Strap", kind="bundle", primary_material=None)

    bc_bag = BundleComponent.objects.create(bundle=bundle, component=bag, quantity=1, is_primary=True)
    bc_strap = BundleComponent.objects.create(bundle=bundle, component=strap, quantity=2, is_primary=False)

    response = client.post(
        reverse("orders_create"),
        data={
            "product": bundle.id,
            f"bundle_component_{bc_bag.pk}_primary_material_color": bag_color.id,
            f"bundle_component_{bc_strap.pk}_primary_material_color": strap_color.id,
            f"bundle_component_{bc_strap.pk}_is_embroidery": "on",
            "is_etsy": False,
            "is_embroidery": False,
            "is_urgent": False,
            "comment": "Bundle order",
        },
    )
    assert response.status_code == 302

    from apps.production.models import ProductionOrder

    orders = list(ProductionOrder.objects.filter(comment="Bundle order").select_related("product", "variant"))
    assert len(orders) == 3
    assert {o.product_id for o in orders} == {bag.id, strap.id}
    assert any(o.product_id == bag.id and o.variant.primary_material_color_id == bag_color.id for o in orders)
    assert sum(1 for o in orders if o.product_id == strap.id and o.variant.primary_material_color_id == strap_color.id) == 2
    assert any(o.product_id == strap.id and o.is_embroidery is True for o in orders)
    assert all(o.is_embroidery is False for o in orders if o.product_id == bag.id)


@pytest.mark.django_db(transaction=True)
def test_orders_create_hides_embroidery_when_product_disallows_it(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    from apps.materials.models import Material

    material = Material.objects.create(name="NoEmb material")
    color = ColorFactory(material=material, name="NoEmb color", code=3333)
    model = ProductFactory(primary_material=material, allows_embroidery=False)

    response = client.get(reverse("orders_create"), {"product": model.id})
    assert response.status_code == 200
    assert b'name="is_embroidery"' not in response.content

    response2 = client.post(
        reverse("orders_create"),
        data={
            "product": model.id,
            "primary_material_color": color.id,
            "is_etsy": False,
            "is_embroidery": True,
            "is_urgent": False,
            "comment": "NoEmb order",
        },
    )
    assert response2.status_code == 302

    from apps.production.models import ProductionOrder

    order = ProductionOrder.objects.get(comment="NoEmb order")
    assert order.is_embroidery is False
