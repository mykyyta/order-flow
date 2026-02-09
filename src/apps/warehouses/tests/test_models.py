import pytest
from django.db import IntegrityError

from apps.warehouses.models import Warehouse
from apps.warehouses.services import get_default_warehouse


@pytest.mark.django_db
def test_only_one_active_default_warehouse_allowed():
    assert Warehouse.objects.filter(is_default_for_production=True, is_active=True).count() == 1

    with pytest.raises(IntegrityError):
        Warehouse.objects.create(
            name="Backup",
            code="BACKUP",
            kind=Warehouse.Kind.STORAGE,
            is_default_for_production=True,
            is_active=True,
        )


@pytest.mark.django_db
def test_get_default_warehouse_creates_main_if_missing():
    warehouse = get_default_warehouse()

    assert warehouse.code == "MAIN"
    assert warehouse.is_default_for_production is True
    assert warehouse.is_active is True
