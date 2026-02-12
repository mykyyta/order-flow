from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_product_price_retail_uah"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="variant",
            name="catalog_productvariant_color_xor_primary",
        ),
        migrations.AddConstraint(
            model_name="variant",
            constraint=models.UniqueConstraint(
                condition=(
                    models.Q(color__isnull=True)
                    & models.Q(primary_material_color__isnull=True)
                    & models.Q(secondary_material_color__isnull=True)
                ),
                fields=("product",),
                name="catalog_productvariant_uncolored_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="variant",
            constraint=models.CheckConstraint(
                condition=models.Q(color__isnull=True)
                | models.Q(primary_material_color__isnull=True),
                name="catalog_productvariant_color_primary_exclusive",
            ),
        ),
    ]
