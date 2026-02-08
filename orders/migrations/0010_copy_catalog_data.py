# Data migration: copy ProductModel and Color from orders to catalog (preserving IDs)

from django.db import migrations, connection


def copy_to_catalog(apps, schema_editor):
    OrderProductModel = apps.get_model("orders", "ProductModel")
    OrderColor = apps.get_model("orders", "Color")
    CatalogProductModel = apps.get_model("catalog", "ProductModel")
    CatalogColor = apps.get_model("catalog", "Color")

    for obj in OrderProductModel.objects.iterator():
        CatalogProductModel.objects.create(id=obj.id, name=obj.name)

    for obj in OrderColor.objects.iterator():
        CatalogColor.objects.create(
            id=obj.id,
            name=obj.name,
            code=obj.code,
            availability_status=obj.availability_status,
        )

    # Update sequences so next INSERT gets correct id (PostgreSQL).
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('catalog_productmodel', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM catalog_productmodel))"
            )
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('catalog_color', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM catalog_color))"
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0009_add_completed_orders_index"),
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_to_catalog, noop_reverse),
    ]
