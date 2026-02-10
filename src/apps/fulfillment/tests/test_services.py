from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.catalog.models import Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.fulfillment.services import (
    complete_production_order,
    create_production_orders_for_sales_order,
    create_sales_order_orchestrated,
    receive_purchase_order_line_orchestrated,
    scrap_wip,
    transfer_finished_stock_orchestrated,
    transfer_material_stock_orchestrated,
)
from apps.inventory.models import ProductStockMovement, WIPStockMovement
from apps.inventory.services import add_to_stock, add_to_wip_stock, get_stock_quantity
from apps.materials.models import (
    Material,
    MaterialStockMovement,
    MaterialStock,
    MaterialStockTransfer,
    BOM,
)
from apps.materials.services import add_material_stock
from apps.production.domain.status import STATUS_FINISHED
from apps.accounts.tests.conftest import UserFactory
from apps.materials.models import GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier
from apps.sales.models import SalesOrder
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_create_sales_order_orchestrated_creates_sales_order():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    color = ColorFactory()

    order = create_sales_order_orchestrated(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Оркестрація",
        lines_data=[
            {
                "product_id": model.id,
                "color_id": color.id,
                "quantity": 1,
            }
        ],
        created_by=user,
    )

    assert order.lines.count() == 1


@pytest.mark.django_db
def test_create_production_orders_for_sales_order_orchestrated():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    color = ColorFactory()
    order = create_sales_order_orchestrated(
        source=SalesOrder.Source.WHOLESALE,
        customer_info="ТОВ Plan",
        lines_data=[
            {
                "product_id": model.id,
                "color_id": color.id,
                "quantity": 2,
            }
        ],
        created_by=user,
    )

    with patch("apps.production.services.send_order_created"):
        created_orders = create_production_orders_for_sales_order(
            sales_order=order,
            created_by=user,
        )

    assert len(created_orders) == 2


@pytest.mark.django_db
def test_receive_purchase_order_line_orchestrated_updates_received_quantity():
    user = UserFactory()
    supplier = Supplier.objects.create(name="Supplier Fulfillment")
    material = Material.objects.create(name="Thread Fulfillment")
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.SENT,
        created_by=user,
    )
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("10.000"),
        unit=BOM.Unit.PIECE,
    )

    receive_purchase_order_line_orchestrated(
        purchase_order_line=line,
        quantity=Decimal("4.000"),
        received_by=user,
    )
    line.refresh_from_db()
    assert line.received_quantity == Decimal("4.000")


@pytest.mark.django_db
def test_complete_production_order_orchestrated():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    color = ColorFactory()
    with patch("apps.production.services.send_order_created"), patch("apps.production.services.send_order_finished"):
        order = create_production_orders_for_sales_order(
            sales_order=create_sales_order_orchestrated(
                source=SalesOrder.Source.SITE,
                customer_info="Complete production",
                lines_data=[
                    {
                        "product_id": model.id,
                        "color_id": color.id,
                        "quantity": 1,
                    }
                ],
                created_by=user,
            ),
            created_by=user,
        )[0]
        complete_production_order(production_order=order, changed_by=user)

    order.refresh_from_db()
    assert order.status == STATUS_FINISHED


@pytest.mark.django_db
def test_scrap_wip_orchestrated():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    variant = Variant.objects.create(product=model, color=ColorFactory())
    add_to_wip_stock(
        variant_id=variant.id,
        quantity=3,
        reason=WIPStockMovement.Reason.CUTTING_IN,
        user=user,
    )

    record = scrap_wip(
        variant_id=variant.id,
        quantity=1,
        user=user,
    )

    assert record.quantity == 2


@pytest.mark.django_db
def test_transfer_finished_stock_orchestrated():
    user = UserFactory()
    model = ProductFactory(is_bundle=False)
    variant = Variant.objects.create(product=model, color=ColorFactory())
    from_warehouse = Warehouse.objects.create(
        name="From Fulfillment Finished",
        code="FUL-FIN-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Fulfillment Finished",
        code="FUL-FIN-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    add_to_stock(
        warehouse_id=from_warehouse.id,
        variant_id=variant.id,
        quantity=3,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
        user=user,
    )

    transfer = transfer_finished_stock_orchestrated(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
        variant_id=variant.id,
        quantity=2,
        user=user,
    )

    assert transfer.status == transfer.Status.COMPLETED
    assert get_stock_quantity(warehouse_id=from_warehouse.id, variant_id=variant.id) == 1
    assert get_stock_quantity(warehouse_id=to_warehouse.id, variant_id=variant.id) == 2


@pytest.mark.django_db
def test_transfer_material_stock_orchestrated():
    user = UserFactory()
    material = Material.objects.create(name="Fulfillment material transfer")
    from_warehouse = Warehouse.objects.create(
        name="From Fulfillment Material",
        code="FUL-MAT-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Fulfillment Material",
        code="FUL-MAT-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    add_material_stock(
        warehouse_id=from_warehouse.id,
        material=material,
        quantity=Decimal("3.000"),
        unit=BOM.Unit.PIECE,
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
        created_by=user,
    )

    transfer = transfer_material_stock_orchestrated(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
        material=material,
        quantity=Decimal("1.250"),
        unit=BOM.Unit.PIECE,
        user=user,
    )

    assert transfer.status == transfer.Status.COMPLETED
    assert MaterialStock.objects.get(warehouse_id=from_warehouse.id, material=material).quantity == Decimal(
        "1.750"
    )
    assert MaterialStock.objects.get(warehouse_id=to_warehouse.id, material=material).quantity == Decimal(
        "1.250"
    )


@pytest.mark.django_db
def test_receive_purchase_order_line_orchestrated_rolls_back_when_quantity_exceeds_remaining():
    user = UserFactory()
    supplier = Supplier.objects.create(name="Supplier rollback")
    material = Material.objects.create(name="Thread rollback")
    purchase_order = PurchaseOrder.objects.create(
        supplier=supplier,
        status=PurchaseOrder.Status.SENT,
        created_by=user,
    )
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("2.000"),
        unit=BOM.Unit.PIECE,
    )

    with pytest.raises(ValueError, match="remaining quantity"):
        receive_purchase_order_line_orchestrated(
            purchase_order_line=line,
            quantity=Decimal("3.000"),
            received_by=user,
        )

    line.refresh_from_db()
    assert line.received_quantity == Decimal("0.000")
    assert not GoodsReceiptLine.objects.filter(purchase_order_line=line).exists()


@pytest.mark.django_db
def test_transfer_material_stock_orchestrated_rolls_back_when_not_enough_stock():
    user = UserFactory()
    material = Material.objects.create(name="Fulfillment transfer rollback")
    from_warehouse = Warehouse.objects.create(
        name="From Fulfillment Rollback",
        code="FUL-MAT-RB-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Fulfillment Rollback",
        code="FUL-MAT-RB-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(ValueError, match="Недостатньо на складі"):
        transfer_material_stock_orchestrated(
            from_warehouse_id=from_warehouse.id,
            to_warehouse_id=to_warehouse.id,
            material=material,
            quantity=Decimal("0.500"),
            unit=BOM.Unit.PIECE,
            user=user,
        )

    assert not MaterialStockTransfer.objects.filter(
        from_warehouse_id=from_warehouse.id,
        to_warehouse_id=to_warehouse.id,
    ).exists()
