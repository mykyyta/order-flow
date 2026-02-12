# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="section",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]
