from unittest.mock import patch

import pytest

from apps.catalog.tests.conftest import ColorFactory, ProductModelFactory
from apps.production.domain.status import STATUS_FINISHED
from apps.orders.tests.conftest import UserFactory
from apps.production.services import change_production_order_status, create_production_order


@pytest.mark.django_db
def test_create_and_change_production_order_status_via_production_context():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()

    with patch("apps.orders.services.send_order_created"), patch("apps.orders.services.send_order_finished"):
        order = create_production_order(
            model=model,
            color=color,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment="production wrapper",
            created_by=user,
            orders_url=None,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )

    order.refresh_from_db()
    assert order.current_status == STATUS_FINISHED
