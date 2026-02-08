# Generated manually for catalog app extraction

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ProductModel",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Color",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True)),
                ("code", models.IntegerField(unique=True)),
                (
                    "availability_status",
                    models.CharField(
                        choices=[
                            ("in_stock", "В наявності"),
                            ("low_stock", "Закінчується"),
                            ("out_of_stock", "Немає"),
                        ],
                        default="in_stock",
                        max_length=20,
                    ),
                ),
            ],
        ),
    ]
