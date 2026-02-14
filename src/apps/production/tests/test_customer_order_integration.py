"""Tests for production and sales integration with inventory."""
from unittest.mock import patch

import pytest

from apps.catalog.models import Variant
from apps.inventory.models import ProductStockMovement, ProductStock
from apps.production.domain.status import STATUS_DONE
from apps.production.services import change_production_order_status, create_production_order
from apps.materials.models import Material, MaterialColor
from apps.sales.models import SalesOrder, SalesOrderLine

from .conftest import ColorFactory, ProductFactory, UserFactory


@pytest.mark.django_db
def test_change_order_status_finished_adds_item_to_stock_for_customer_line():
    user = UserFactory()
    color = ColorFactory()
    model = ProductFactory(kind="standard", primary_material=color.material)
    sales_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Інтеграція",
    )
    line = SalesOrderLine.objects.create(
        sales_order=sales_order,
        product=model,
        variant=Variant.objects.create(product=model, primary_material_color=color),
        quantity=1,
    )

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            product=model,
            primary_material_color=color,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
            sales_order_line=line,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_DONE,
            changed_by=user,
        )

    record = ProductStock.objects.get(variant=order.variant)
    assert record.quantity == 1

    movement = ProductStockMovement.objects.get(related_production_order=order)
    assert movement.quantity_change == 1
    assert movement.reason == ProductStockMovement.Reason.PRODUCTION_IN


@pytest.mark.django_db
def test_change_order_status_finished_uses_material_color_stock_key():
    user = UserFactory()
    felt = Material.objects.create(name="Felt", stock_unit="pcs")
    leather = Material.objects.create(name="Leather smooth", stock_unit="pcs")
    blue = MaterialColor.objects.create(material=felt, name="Blue", code=77)
    black = MaterialColor.objects.create(material=leather, name="Black", code=7)
    product = ProductFactory(
        kind="standard",
        primary_material=felt,
        secondary_material=leather,
    )
    sales_order = SalesOrder.objects.create(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Матеріал",
    )
    line = SalesOrderLine.objects.create(
        sales_order=sales_order,
        product=product,
        quantity=1,
        variant=Variant.objects.create(
            product=product,
            primary_material_color=blue,
            secondary_material_color=black,
        ),
    )

    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_order(
            product=product,
            primary_material_color=blue,
            secondary_material_color=black,
            is_embroidery=False,
            is_urgent=False,
            is_etsy=False,
            comment=None,
            created_by=user,
            orders_url=None,
            sales_order_line=line,
        )
        change_production_order_status(
            production_orders=[order],
            new_status=STATUS_DONE,
            changed_by=user,
        )

    record = ProductStock.objects.get(variant=order.variant)
    assert record.quantity == 1
