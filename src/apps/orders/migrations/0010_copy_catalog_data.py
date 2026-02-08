# Data migration: copy ProductModel and Color from orders to catalog (preserving IDs)

from django.db import connection, migrations


def copy_to_catalog(apps, schema_editor):
    OrderProductModel = apps.get_model("orders", "ProductModel")
    OrderColor = apps.get_model("orders", "Color")
    CatalogProductModel = apps.get_model("catalog", "ProductModel")
    CatalogColor = apps.get_model("catalog", "Color")
    Order = apps.get_model("orders", "Order")

    for obj in OrderProductModel.objects.iterator():
        CatalogProductModel.objects.create(id=obj.id, name=obj.name)

    for obj in OrderColor.objects.iterator():
        CatalogColor.objects.create(
            id=obj.id,
            name=obj.name,
            code=obj.code,
            availability_status=obj.availability_status,
        )

    # Safety: ensure every Order row has model_id/color_id present in catalog (should hold by FK).
    catalog_model_ids = set(CatalogProductModel.objects.values_list("id", flat=True))
    catalog_color_ids = set(CatalogColor.objects.values_list("id", flat=True))
    for order in Order.objects.only("model_id", "color_id").iterator():
        if order.model_id not in catalog_model_ids:
            raise RuntimeError(
                f"Order {order.id} has model_id={order.model_id} not in catalog_productmodel."
            )
        if order.color_id not in catalog_color_ids:
            raise RuntimeError(
                f"Order {order.id} has color_id={order.color_id} not in catalog_color."
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
