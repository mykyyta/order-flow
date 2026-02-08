# Alter Order.model and Order.color to reference catalog.ProductModel and catalog.Color.
# Data was already copied in 0010; model_id and color_id values are valid in catalog tables.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("orders", "0010_copy_catalog_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="model",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="catalog.productmodel",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="color",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="catalog.color",
            ),
        ),
    ]
