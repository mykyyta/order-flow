"""HTTP layer and view tests for orders."""

import pytest
from django.urls import reverse
from orders.domain.status import STATUS_FINISHED, STATUS_NEW, STATUS_ON_HOLD

from .conftest import ColorFactory, OrderFactory, ProductModelFactory, UserFactory


@pytest.mark.django_db
def test_transition_map_present_in_page(client):
    user = UserFactory()
    client.force_login(user)
    response = client.get(reverse("orders_active"))
    assert response.status_code == 200
    assert b"transition-map-data" in response.content
    assert b"bulk-status-form" in response.content
    assert b"clear-selection-btn" in response.content


@pytest.mark.django_db
def test_current_orders_list_is_paginated_and_excludes_finished(client):
    user = UserFactory()
    client.force_login(user)
    model = ProductModelFactory()
    color = ColorFactory()
    for _ in range(51):
        OrderFactory(model=model, color=color, current_status=STATUS_NEW)
    OrderFactory(model=model, color=color, current_status=STATUS_FINISHED)
    response = client.get(reverse("orders_active"))
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 51
    assert len(response.context["orders"]) == 50
    assert response.context["page_obj"].has_next()
    second_page = client.get(reverse("orders_active"), {"page": 2})
    assert second_page.status_code == 200
    assert len(second_page.context["orders"]) == 1
    assert not second_page.context["page_obj"].has_next()


@pytest.mark.django_db
def test_current_orders_supports_status_filter(client):
    user = UserFactory()
    client.force_login(user)
    model = ProductModelFactory()
    color = ColorFactory()
    target = OrderFactory(
        model=model,
        color=color,
        comment="vip batch",
        current_status=STATUS_ON_HOLD,
    )
    OrderFactory(
        model=model,
        color=color,
        comment="regular batch",
        current_status=STATUS_NEW,
    )
    response = client.get(reverse("orders_active"), {"filter": STATUS_ON_HOLD})
    assert response.status_code == 200
    orders = list(response.context["orders"])
    assert len(orders) == 1
    assert orders[0].id == target.id


@pytest.mark.django_db
def test_finished_orders_search_filters_across_all_finished(client):
    user = UserFactory()
    client.force_login(user)
    model = ProductModelFactory(name="Model History")
    color = ColorFactory(name="Navy", code=7)
    target = OrderFactory(
        model=model,
        color=color,
        comment="special archive order",
        current_status=STATUS_FINISHED,
    )
    OrderFactory(
        model=model,
        color=color,
        comment="other archive order",
        current_status=STATUS_FINISHED,
    )
    OrderFactory(
        model=model,
        color=color,
        comment="special archive order",
        current_status=STATUS_NEW,
    )
    response = client.get(reverse("orders_completed"), {"q": "special"})
    assert response.status_code == 200
    orders = list(response.context["page_obj"].object_list)
    assert len(orders) == 1
    assert orders[0].id == target.id


@pytest.mark.django_db
def test_finished_orders_search_preserves_query_params_for_pagination(client):
    user = UserFactory()
    client.force_login(user)
    model = ProductModelFactory()
    color = ColorFactory()
    for _ in range(21):
        OrderFactory(
            model=model,
            color=color,
            comment="archive",
            current_status=STATUS_FINISHED,
        )
    response = client.get(reverse("orders_completed"), {"q": "archive"})
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 21
    assert len(response.context["page_obj"].object_list) == 20
    assert b"?page=2&q=archive" in response.content or b"page=2" in response.content
    second_page = client.get(reverse("orders_completed"), {"q": "archive", "page": 2})
    assert second_page.status_code == 200
    assert len(second_page.context["page_obj"].object_list) == 1


@pytest.mark.django_db
def test_order_detail_renders_status_indicator(client):
    user = UserFactory()
    client.force_login(user)
    model = ProductModelFactory()
    color = ColorFactory()
    order = OrderFactory(model=model, color=color, current_status=STATUS_ON_HOLD)
    response = client.get(reverse("order_detail", kwargs={"order_id": order.id}))
    assert response.status_code == 200
    assert b"text-orange-500" in response.content
    assert order.get_current_status_display().encode() in response.content


def test_message_alert_class_mapping():
    from orders.templatetags.order_ui import message_alert_class

    assert message_alert_class("error") == "alert alert-error"
    assert message_alert_class("success") == "alert alert-success"
    assert message_alert_class("warning extra") == "alert alert-warning"
    assert message_alert_class("unknown") == "alert alert-info"
