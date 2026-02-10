"""HTTP layer and view tests for orders."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.production.domain.status import STATUS_FINISHED, STATUS_NEW, STATUS_ON_HOLD

from .conftest import ColorFactory, OrderFactory, ProductModelFactory, UserFactory

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
    model = ProductModelFactory()
    color = ColorFactory()
    OrderFactory(
        model=model,
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
    model = ProductModelFactory()
    color = ColorFactory()
    for _ in range(51):
        OrderFactory(model=model, color=color, status=STATUS_NEW)
    OrderFactory(model=model, color=color, status=STATUS_FINISHED)
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
    model = ProductModelFactory()
    color = ColorFactory()
    target = OrderFactory(
        model=model,
        color=color,
        comment="vip batch",
        status=STATUS_ON_HOLD,
    )
    OrderFactory(
        model=model,
        color=color,
        comment="regular batch",
        status=STATUS_NEW,
    )
    response = client.get(reverse("orders_active"), {"filter": STATUS_ON_HOLD})
    assert response.status_code == 200
    orders = list(response.context["orders"])
    assert len(orders) == 1
    assert orders[0].id == target.id


@pytest.mark.django_db(transaction=True)
def test_finished_orders_search_filters_across_all_finished(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)
    model = ProductModelFactory(name="Model History")
    color = ColorFactory(name="Navy", code=7)
    target = OrderFactory(
        model=model,
        color=color,
        comment="special archive order",
        status=STATUS_FINISHED,
    )
    OrderFactory(
        model=model,
        color=color,
        comment="other archive order",
        status=STATUS_FINISHED,
    )
    OrderFactory(
        model=model,
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
    model = ProductModelFactory()
    color = ColorFactory()
    for _ in range(21):
        OrderFactory(
            model=model,
            color=color,
            comment="archive",
            status=STATUS_FINISHED,
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
    model = ProductModelFactory()
    color = ColorFactory()
    order = OrderFactory(model=model, color=color, status=STATUS_ON_HOLD)
    response = client.get(reverse("order_detail", kwargs={"pk": order.id}))
    assert response.status_code == 200
    assert b"text-orange-500" in response.content
    assert order.get_status_display().encode() in response.content


@pytest.mark.django_db(transaction=True)
def test_orders_create_hides_archived_catalog_items(client):
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    active_model = ProductModelFactory(name="Active model")
    archived_model = ProductModelFactory(name="Archived model", archived_at=timezone.now())
    active_color = ColorFactory(name="Active color", code=1001, status="in_stock")
    archived_color = ColorFactory(
        name="Archived color",
        code=2002,
        status="in_stock",
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

    model = ProductModelFactory(name="Model to archive")
    color = ColorFactory(name="Color to archive", code=888, status="in_stock")
    order = OrderFactory(model=model, color=color, status=STATUS_NEW)

    model.archived_at = timezone.now()
    model.save(update_fields=["archived_at"])
    color.archived_at = timezone.now()
    color.save(update_fields=["archived_at"])

    response = client.get(reverse("order_edit", kwargs={"pk": order.id}))
    assert response.status_code == 200
    assert model.name.encode() in response.content
    assert color.name.encode() in response.content


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
    model = ProductModelFactory()
    color = ColorFactory()
    order1 = OrderFactory(model=model, color=color, status=STATUS_NEW)
    order2 = OrderFactory(model=model, color=color, status=STATUS_NEW)

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [order1.id, order2.id], "new_status": "doing"},
    )
    assert response.status_code == 302
    order1.refresh_from_db()
    order2.refresh_from_db()
    assert order1.status == "doing"
    assert order2.status == "doing"


@pytest.mark.django_db(transaction=True)
def test_orders_bulk_status_empty_selection_shows_error(client):
    """Empty orders selection causes form validation error."""
    user = UserFactory()
    client.force_login(user, backend=AUTH_BACKEND)

    response = client.post(
        reverse("orders_bulk_status"),
        data={"orders": [], "new_status": "doing"},
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
    model = ProductModelFactory()
    color = ColorFactory()
    order = OrderFactory(model=model, color=color, status=STATUS_NEW)

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
    model = ProductModelFactory()
    color = ColorFactory()
    # Order with status "doing" cannot transition back to "new"
    order = OrderFactory(model=model, color=color, status="doing")

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
    model = ProductModelFactory()
    color = ColorFactory()

    response = client.post(
        reverse("orders_create"),
        data={
            "model": model.id,
            "color": color.id,
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
    assert order.variant.color == color
    assert order.status == STATUS_NEW
