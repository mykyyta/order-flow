from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0015_alter_order_color_alter_order_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="theme",
            field=models.CharField(
                choices=[
                    ("lumen_subtle", "Lumen (Subtle)"),
                    ("lumen_warm", "Lumen (Warm)"),
                    ("dune_lite", "Dune Lite"),
                ],
                default="lumen_subtle",
                max_length=32,
                verbose_name="Theme",
            ),
        ),
    ]
