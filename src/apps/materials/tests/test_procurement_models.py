"""Tests for suppliers, stock, and purchasing models."""
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.materials.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    Material,
    MaterialMovement,
    MaterialStockRecord,
    ProductMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierMaterialOffer,
)
from apps.orders.tests.conftest import UserFactory


@pytest.mark.django_db
def test_supplier_material_offer_allows_multiple_offers_per_material():
    supplier = Supplier.objects.create(name="Supplier A")
    material = Material.objects.create(name="Felt")

    SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=ProductMaterial.Unit.SQUARE_METER,
        price_per_unit=Decimal("12.50"),
    )
    SupplierMaterialOffer.objects.create(
        supplier=supplier,
        material=material,
        unit=ProductMaterial.Unit.SQUARE_METER,
        price_per_unit=Decimal("11.90"),
        min_order_quantity=Decimal("10.000"),
    )

    assert SupplierMaterialOffer.objects.filter(supplier=supplier, material=material).count() == 2


@pytest.mark.django_db
def test_material_stock_record_unique_per_material_color_and_unit():
    material = Material.objects.create(name="Felt")

    MaterialStockRecord.objects.create(
        material=material,
        unit=ProductMaterial.Unit.SQUARE_METER,
        quantity=Decimal("5.000"),
    )

    with pytest.raises(IntegrityError):
        MaterialStockRecord.objects.create(
            material=material,
            unit=ProductMaterial.Unit.SQUARE_METER,
            quantity=Decimal("1.000"),
        )


@pytest.mark.django_db
def test_purchase_order_line_remaining_quantity_property():
    supplier = Supplier.objects.create(name="Supplier B")
    material = Material.objects.create(name="Leather")
    user = UserFactory()
    purchase_order = PurchaseOrder.objects.create(supplier=supplier, created_by=user)
    line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("100.000"),
        received_quantity=Decimal("40.000"),
        unit=ProductMaterial.Unit.PIECE,
        unit_price=Decimal("3.50"),
    )

    assert line.remaining_quantity == Decimal("60.000")


@pytest.mark.django_db
def test_goods_receipt_line_links_purchase_line_and_stock_movement():
    supplier = Supplier.objects.create(name="Supplier C")
    material = Material.objects.create(name="Glue")
    user = UserFactory()
    purchase_order = PurchaseOrder.objects.create(supplier=supplier, created_by=user)
    po_line = PurchaseOrderLine.objects.create(
        purchase_order=purchase_order,
        material=material,
        quantity=Decimal("10.000"),
        unit=ProductMaterial.Unit.MILLILITER,
        unit_price=Decimal("0.20"),
    )
    stock_record = MaterialStockRecord.objects.create(
        material=material,
        unit=ProductMaterial.Unit.MILLILITER,
        quantity=Decimal("0.000"),
    )
    receipt = GoodsReceipt.objects.create(
        supplier=supplier,
        purchase_order=purchase_order,
        received_by=user,
    )
    receipt_line = GoodsReceiptLine.objects.create(
        receipt=receipt,
        purchase_order_line=po_line,
        material=material,
        quantity=Decimal("10.000"),
        unit=ProductMaterial.Unit.MILLILITER,
    )
    movement = MaterialMovement.objects.create(
        stock_record=stock_record,
        quantity_change=Decimal("10.000"),
        reason=MaterialMovement.Reason.PURCHASE_IN,
        related_purchase_order_line=po_line,
        related_receipt_line=receipt_line,
        created_by=user,
    )

    assert movement.related_purchase_order_line == po_line
    assert movement.related_receipt_line == receipt_line
