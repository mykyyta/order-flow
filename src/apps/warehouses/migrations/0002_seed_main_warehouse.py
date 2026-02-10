from django.db import migrations


def seed_main_warehouse(apps, schema_editor):
    Warehouse = apps.get_model("warehouses", "Warehouse")
    warehouse, _ = Warehouse.objects.get_or_create(
        code="MAIN",
        defaults={
            "name": "Основний склад",
            "kind": "storage",
            "is_default_for_production": True,
            "is_active": True,
        },
    )

    updates = []
    if warehouse.name != "Основний склад":
        warehouse.name = "Основний склад"
        updates.append("name")
    if warehouse.kind != "storage":
        warehouse.kind = "storage"
        updates.append("kind")
    if warehouse.is_default_for_production is False:
        warehouse.is_default_for_production = True
        updates.append("is_default_for_production")
    if warehouse.is_active is False:
        warehouse.is_active = True
        updates.append("is_active")
    if updates:
        warehouse.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("warehouses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_main_warehouse, migrations.RunPython.noop),
    ]
