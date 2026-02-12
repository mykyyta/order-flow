import pytest
from django.db import IntegrityError

from apps.catalog.models import Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.inventory.models import ProductStockTransfer, ProductStockTransferLine
from apps.accounts.tests.conftest import UserFactory
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_finished_stock_transfer_requires_different_warehouses():
    user = UserFactory()
    warehouse = Warehouse.objects.create(
        name="Main Transfer",
        code="TR-MAIN",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(IntegrityError):
        ProductStockTransfer.objects.create(
            from_warehouse=warehouse,
            to_warehouse=warehouse,
            created_by=user,
        )


@pytest.mark.django_db
def test_finished_stock_transfer_line_unique_variant_per_transfer():
    user = UserFactory()
    from_warehouse = Warehouse.objects.create(
        name="From WH",
        code="TR-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To WH",
        code="TR-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    transfer = ProductStockTransfer.objects.create(
        from_warehouse=from_warehouse,
        to_warehouse=to_warehouse,
        created_by=user,
    )
    variant = Variant.objects.create(
        product=ProductFactory(is_bundle=False),
        color=ColorFactory(),
    )

    ProductStockTransferLine.objects.create(
        transfer=transfer,
        variant=variant,
        quantity=2,
    )
    with pytest.raises(IntegrityError):
        ProductStockTransferLine.objects.create(
            transfer=transfer,
            variant=variant,
            quantity=1,
        )
