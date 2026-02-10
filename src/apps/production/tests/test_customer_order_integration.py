"""Tests for production and sales integration with inventory."""
from unittest.mock import patch

import pytest

from apps.inventory.models import StockMovement, StockRecord
from apps.production.domain.status import STATUS_FINISHED
from apps.production.services import change_production_order_status, create_production_order
from apps.materials.models import Material, MaterialColor
from apps.sales.models import SalesOrder, SalesOrderLine

from .conftest import ColorFactory, ProductModelFactory, UserFactory


@pytest.mark.django_db
def test_change_order_status_finished_adds_item_to_stock_for_customer_line():
    user = UserFactory()
    model = ProductModelFactory(is_bundle=False)
    color = ColorFactory()
    customer_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Інтеграція",
    )
    line = SalesOrderLine.objects.create(
        customer_order=customer_order,
        product_model=model,
        color=color,
        quantity=1,
    )

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            model=model,
            color=color,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
            customer_order_line=line,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )

    record = StockRecord.objects.get(product_variant=order.product_variant)
    assert record.quantity == 1

    movement = StockMovement.objects.get(related_production_order=order)
    assert movement.quantity_change == 1
    assert movement.reason == StockMovement.Reason.PRODUCTION_IN


@pytest.mark.django_db
def test_change_order_status_finished_uses_material_color_stock_key():
    user = UserFactory()
    felt = Material.objects.create(name="Felt")
    leather = Material.objects.create(name="Leather smooth")
    blue = MaterialColor.objects.create(material=felt, name="Blue", code=77)
    black = MaterialColor.objects.create(material=leather, name="Black", code=7)
    product = ProductModelFactory(
        is_bundle=False,
        primary_material=felt,
        secondary_material=leather,
    )
    customer_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Матеріал",
    )
    line = SalesOrderLine.objects.create(
        customer_order=customer_order,
        product_model=product,
        quantity=1,
        primary_material_color=blue,
        secondary_material_color=black,
    )

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            model=product,
            color=None,
            primary_material_color=blue,
            secondary_material_color=black,
            embroidery=False,
            urgent=False,
            etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
            customer_order_line=line,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_FINISHED,
            changed_by=user,
        )

    record = StockRecord.objects.get(product_variant=order.product_variant)
    assert record.quantity == 1
