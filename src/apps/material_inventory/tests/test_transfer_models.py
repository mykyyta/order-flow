from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.material_inventory.models import MaterialStockTransfer, MaterialStockTransferLine
from apps.materials.models import Material, MaterialColor, ProductMaterial
from apps.accounts.tests.conftest import UserFactory
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_material_stock_transfer_requires_different_warehouses():
    user = UserFactory()
    warehouse = Warehouse.objects.create(
        name="Material Main",
        code="MAT-MAIN",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )

    with pytest.raises(IntegrityError):
        MaterialStockTransfer.objects.create(
            from_warehouse=warehouse,
            to_warehouse=warehouse,
            created_by=user,
        )


@pytest.mark.django_db
def test_material_stock_transfer_line_validates_material_color_belongs_to_material():
    user = UserFactory()
    from_warehouse = Warehouse.objects.create(
        name="From Material",
        code="MAT-FROM",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    to_warehouse = Warehouse.objects.create(
        name="To Material",
        code="MAT-TO",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    transfer = MaterialStockTransfer.objects.create(
        from_warehouse=from_warehouse,
        to_warehouse=to_warehouse,
        created_by=user,
    )
    felt = Material.objects.create(name="Felt transfer")
    leather = Material.objects.create(name="Leather transfer")
    wrong_color = MaterialColor.objects.create(material=leather, name="Black", code=911)

    line = MaterialStockTransferLine(
        transfer=transfer,
        material=felt,
        material_color=wrong_color,
        quantity=Decimal("1.000"),
        unit=ProductMaterial.Unit.SQUARE_METER,
    )

    with pytest.raises(ValidationError, match="must belong"):
        line.full_clean()
