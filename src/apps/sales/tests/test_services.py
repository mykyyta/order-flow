from unittest.mock import patch

import pytest

from apps.customer_orders.models import CustomerOrder
from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.orders.tests.conftest import UserFactory
from apps.sales.services import create_sales_order


@pytest.mark.django_db
def test_create_sales_order_delegates_to_customer_order_service():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()

    with patch("apps.orders.services.send_order_created"):
        order = create_sales_order(
            source=CustomerOrder.Source.WHOLESALE,
            customer_info="ТОВ Продаж",
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

    assert order.lines.count() == 1
