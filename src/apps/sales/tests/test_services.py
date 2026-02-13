from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.accounts.tests.conftest import UserFactory
from apps.sales.models import SalesOrder
from apps.sales.services import create_production_orders_for_sales_order, create_sales_order


@pytest.mark.django_db
def test_create_sales_order_delegates_to_customer_order_service():
    user = UserFactory()
    model = ProductFactory(kind="standard")
    color = ColorFactory()

    with patch("apps.production.services.send_order_created"):
        order = create_sales_order(
            source=SalesOrder.Source.WHOLESALE,
            customer_info="ТОВ Продаж",
            lines_data=[
                {
                    "product_id": model.id,
                    "color_id": color.id,
                    "quantity": 1,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

    assert order.lines.count() == 1


@pytest.mark.django_db
@override_settings(FREEZE_LEGACY_WRITES=True)
def test_create_production_orders_for_sales_order_works_when_legacy_writes_are_frozen():
    user = UserFactory()
    model = ProductFactory(kind="standard")
    color = ColorFactory()
    order = create_sales_order(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Продаж",
        lines_data=[
            {
                "product_id": model.id,
                "color_id": color.id,
                "quantity": 1,
            }
        ],
        create_production_orders=False,
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        created_orders = create_production_orders_for_sales_order(
            sales_order=order,
            created_by=user,
        )

    assert len(created_orders) == 1


@pytest.mark.django_db
@override_settings(FREEZE_LEGACY_WRITES=True)
def test_create_sales_order_with_production_orders_works_when_legacy_writes_are_frozen():
    user = UserFactory()
    model = ProductFactory(kind="standard")
    color = ColorFactory()

    with patch("apps.production.services.send_order_created"):
        order = create_sales_order(
            source=SalesOrder.Source.WHOLESALE,
            customer_info="ТОВ Продаж",
            lines_data=[
                {
                    "product_id": model.id,
                    "color_id": color.id,
                    "quantity": 1,
                }
            ],
            create_production_orders=True,
            created_by=user,
        )

    assert order.lines.count() == 1
    assert order.lines.get().production_orders.count() == 1


@pytest.mark.django_db
def test_create_sales_order_rejects_component_product():
    component = ProductFactory(kind="component")
    color = ColorFactory()

    with pytest.raises(ValueError, match="не можна продавати"):
        create_sales_order(
            source=SalesOrder.Source.WHOLESALE,
            customer_info="ТОВ Компонент",
            lines_data=[
                {
                    "product_id": component.id,
                    "color_id": color.id,
                    "quantity": 1,
                }
            ],
            create_production_orders=False,
        )
