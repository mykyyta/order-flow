# Remove ProductModel and Color from orders app (moved to catalog); drop old tables.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0011_alter_order_fk_to_catalog"),
    ]

    operations = [
        migrations.DeleteModel(name="ProductModel"),
        migrations.DeleteModel(name="Color"),
    ]
