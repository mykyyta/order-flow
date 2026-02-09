"""Integration tests for production planning from customer orders."""
from unittest.mock import patch

import pytest

from apps.customer_orders.models import CustomerOrder, CustomerOrderLine
from apps.customer_orders.services import create_customer_order
from apps.inventory.models import StockMovement
from apps.inventory.services import add_to_stock
from apps.orders.domain.status import STATUS_FINISHED
from apps.orders.models import Order
from apps.orders.services import change_order_status
from apps.orders.tests.conftest import UserFactory
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory



@pytest.mark.django_db
def test_auto_mode_creates_only_missing_production_orders_and_syncs_statuses():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    add_to_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=1,
        reason=StockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    with patch("apps.orders.services.send_order_created"), patch("apps.orders.services.send_order_finished"):
        customer_order = create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="ТОВ Опт",
            lines_data=[
                {
                    "product_model_id": model.id,
                    "color_id": color.id,
                    "quantity": 3,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

        line = customer_order.lines.get()
        assert customer_order.status == CustomerOrder.Status.PRODUCTION
        assert line.production_status == CustomerOrderLine.ProductionStatus.PENDING

        production_orders = Order.objects.filter(customer_order_line=line).order_by("id")
        assert production_orders.count() == 2

        change_order_status(
            orders=[production_orders.first()],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )
        line.refresh_from_db()
        customer_order.refresh_from_db()
        assert line.production_status == CustomerOrderLine.ProductionStatus.IN_PROGRESS
        assert customer_order.status == CustomerOrder.Status.PRODUCTION

        change_order_status(
            orders=[production_orders.last()],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )
        line.refresh_from_db()
        customer_order.refresh_from_db()
        assert line.production_status == CustomerOrderLine.ProductionStatus.DONE
        assert customer_order.status == CustomerOrder.Status.READY


@pytest.mark.django_db
def test_force_mode_ignores_stock_and_creates_all_production_orders():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    add_to_stock(
        product_model_id=model.id,
        color_id=color.id,
        quantity=10,
        reason=StockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    with patch("apps.orders.services.send_order_created"):
        customer_order = create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="Force mode",
            lines_data=[
                {
                    "product_model_id": model.id,
                    "color_id": color.id,
                    "quantity": 4,
                    "production_mode": CustomerOrderLine.ProductionMode.FORCE,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

    line = customer_order.lines.get()
    assert Order.objects.filter(customer_order_line=line).count() == 4
    assert line.production_status == CustomerOrderLine.ProductionStatus.PENDING


@pytest.mark.django_db
def test_manual_mode_does_not_create_production_orders():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()

    with patch("apps.orders.services.send_order_created"):
        customer_order = create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="Manual mode",
            lines_data=[
                {
                    "product_model_id": model.id,
                    "color_id": color.id,
                    "quantity": 2,
                    "production_mode": CustomerOrderLine.ProductionMode.MANUAL,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

    line = customer_order.lines.get()
    assert Order.objects.filter(customer_order_line=line).count() == 0
    assert line.production_status == CustomerOrderLine.ProductionStatus.PENDING
    assert customer_order.status == CustomerOrder.Status.PRODUCTION


@pytest.mark.django_db
def test_auto_mode_resolves_stock_by_product_variant_id(monkeypatch):
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    captured_kwargs: dict[str, int | None] = {}

    def fake_get_stock_quantity(**kwargs):
        captured_kwargs.update(kwargs)
        return 1

    monkeypatch.setattr("apps.inventory.services.get_stock_quantity", fake_get_stock_quantity)

    with patch("apps.orders.services.send_order_created"):
        customer_order = create_customer_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="Variant stock lookup",
            lines_data=[
                {
                    "product_model_id": model.id,
                    "color_id": color.id,
                    "quantity": 1,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

    line = customer_order.lines.get()
    assert line.product_variant_id is not None
    assert captured_kwargs == {"product_variant_id": line.product_variant_id}
    assert Order.objects.filter(customer_order_line=line).count() == 0
