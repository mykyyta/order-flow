# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_product_section_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="color",
            name="code",
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),
    ]

