import pytest

from apps.material_inventory.models import MaterialStockMovement
from apps.materials.models import MaterialMovement


@pytest.mark.django_db
def test_material_stock_movement_alias_points_to_legacy_model():
    assert MaterialStockMovement is MaterialMovement
