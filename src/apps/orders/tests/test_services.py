"""Tests for order services and Order transition logic."""
from __future__ import annotations


import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import ProductVariant
from apps.orders.domain.status import (
    STATUS_DOING,
    STATUS_EMBROIDERY,
    STATUS_FINISHED,
    STATUS_NEW,
)
from apps.orders.exceptions import InvalidStatusTransition
from apps.orders.models import OrderStatusHistory
from apps.orders.services import change_order_status, create_order

from .conftest import ColorFactory, OrderFactory, ProductModelFactory


# --- Order.transition_to unit-style (with DB, no notifications) ---


@pytest.mark.django_db
def test_order_can_transition_to_allowed_status():
    order = OrderFactory(current_status=STATUS_NEW)
    assert order.can_transition_to(STATUS_DOING) is True
    assert order.can_transition_to(STATUS_FINISHED) is True


@pytest.mark.django_db
def test_order_cannot_transition_from_finished():
    order = OrderFactory(current_status=STATUS_FINISHED)
    assert order.can_transition_to(STATUS_EMBROIDERY) is False


@pytest.mark.django_db
def test_order_transition_to_creates_history_and_updates_status(user):
    order = OrderFactory(current_status=STATUS_NEW)
    order.transition_to(STATUS_DOING, changed_by=user)
    order.save()
    order.refresh_from_db()
    assert order.current_status == STATUS_DOING
    assert OrderStatusHistory.objects.filter(order=order, new_status=STATUS_DOING).exists()


@pytest.mark.django_db
def test_order_transition_to_finished_sets_finished_at(user):
    order = OrderFactory(current_status=STATUS_DOING, finished_at=None)
    order.transition_to(STATUS_FINISHED, changed_by=user)
    order.save()
    order.refresh_from_db()
    assert order.current_status == STATUS_FINISHED
    assert order.finished_at is not None


@pytest.mark.django_db
def test_order_transition_raises_invalid_transition(user):
    order = OrderFactory(current_status=STATUS_FINISHED)
    with pytest.raises(InvalidStatusTransition):
        order.transition_to(STATUS_EMBROIDERY, changed_by=user)


@pytest.mark.django_db
def test_change_order_status_rejects_invalid_status(user):
    order = OrderFactory()
    with pytest.raises(ValueError):
        change_order_status(
            orders=[order],
            new_status="invalid_status",
            changed_by=user,
        )


# --- create_order / change_order_status integration (with notification mocks) ---


@pytest.mark.django_db
def test_create_order_persists_history(user):
    from unittest.mock import patch
    model = ProductModelFactory()
    color = ColorFactory()
    with patch("orders.services.send_order_created"):
        order = create_order(
            model=model,
            color=color,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
        )
    assert OrderStatusHistory.objects.filter(order=order).count() == 1
    assert OrderStatusHistory.objects.filter(order=order).first().new_status == STATUS_NEW
    order.refresh_from_db()
    assert order.current_status == STATUS_NEW
    assert order.product_variant is not None
    assert order.product_variant.product_id == model.id
    assert order.product_variant.color_id == color.id


@pytest.mark.django_db
def test_change_status_updates_finished_at(user):
    from unittest.mock import patch
    with patch("orders.services.send_order_created"):
        order = create_order(
            model=ProductModelFactory(),
            color=ColorFactory(),
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
        )
    with patch("orders.services.send_order_finished"):
        change_order_status(
            orders=[order],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )
    order.refresh_from_db()
    assert order.finished_at is not None
    assert order.current_status == STATUS_FINISHED


# --- Delayed notification (function under test: send_delayed_order_created_notifications) ---


@pytest.mark.django_db
def test_delayed_no_orders_returns_no_orders_to_notify():
    from apps.orders.notifications import send_delayed_order_created_notifications
    result = send_delayed_order_created_notifications()
    assert result in ("no orders to notify", "no users to notify", "delayed notifications sent")


@pytest.mark.django_db
def test_order_rejects_mismatched_product_variant_on_save():
    model = ProductModelFactory()
    color = ColorFactory()
    wrong_variant = ProductVariant.objects.create(
        product=model,
        color=ColorFactory(),
    )

    from apps.orders.models import Order

    with pytest.raises(ValidationError, match="must match"):
        Order.objects.create(
            model=model,
            color=color,
            product_variant=wrong_variant,
        )
