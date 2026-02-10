from __future__ import annotations

from apps.warehouses.models import Warehouse

DEFAULT_WAREHOUSE_CODE = "MAIN"


def get_default_warehouse() -> Warehouse:
    active_default = Warehouse.objects.filter(
        is_active=True,
        is_default_for_production=True,
    ).first()
    if active_default is not None:
        return active_default

    warehouse, _ = Warehouse.objects.get_or_create(
        code=DEFAULT_WAREHOUSE_CODE,
        defaults={
            "name": "Основний склад",
            "kind": Warehouse.Kind.STORAGE,
            "is_default_for_production": True,
            "is_active": True,
        },
    )
    updates: list[str] = []
    if warehouse.name != "Основний склад":
        warehouse.name = "Основний склад"
        updates.append("name")
    if warehouse.kind != Warehouse.Kind.STORAGE:
        warehouse.kind = Warehouse.Kind.STORAGE
        updates.append("kind")
    if warehouse.is_default_for_production is False:
        warehouse.is_default_for_production = True
        updates.append("is_default_for_production")
    if warehouse.is_active is False:
        warehouse.is_active = True
        updates.append("is_active")
    if updates:
        warehouse.save(update_fields=updates)
    return warehouse
