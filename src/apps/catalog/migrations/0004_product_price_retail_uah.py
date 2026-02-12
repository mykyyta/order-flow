# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_add_product_section"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="price_retail_uah",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]
