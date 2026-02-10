from django.db import migrations


def seed_main_warehouse(apps, schema_editor):
    warehouse_model = apps.get_model("warehouses", "Warehouse")
    warehouse_model.objects.update(is_default_for_production=False)
    warehouse_model.objects.update_or_create(
        code="MAIN",
        defaults={
            "name": "Основний склад",
            "kind": "storage",
            "is_default_for_production": True,
            "is_active": True,
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("warehouses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_main_warehouse, noop_reverse),
    ]
