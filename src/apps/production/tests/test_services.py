from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.production.domain.status import STATUS_DONE
from apps.accounts.tests.conftest import UserFactory
from apps.production.services import change_production_order_status, create_production_order

from .conftest import ColorFactory, ProductFactory


@pytest.mark.django_db
def test_create_and_change_production_order_status_via_production_context():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    color = ColorFactory()

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            product=model,
            primary_material_color=color,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment="production wrapper",
            created_by=user,
            orders_url=None,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_DONE,
            changed_by=user,
        )

    order.refresh_from_db()
    assert order.status == STATUS_DONE


@pytest.mark.django_db
@override_settings(FREEZE_LEGACY_WRITES=True)
def test_production_context_allows_writes_when_legacy_writes_are_frozen():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    color = ColorFactory()

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            product=model,
            primary_material_color=color,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment="production wrapper",
            created_by=user,
            orders_url=None,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_DONE,
            changed_by=user,
        )

    order.refresh_from_db()
    assert order.status == STATUS_DONE
