from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0013_remove_notificationsetting"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="theme",
            field=models.CharField(
                choices=[
                    ("lumen_subtle", "Lumen — м’яка"),
                    ("lumen", "Lumen — базова"),
                    ("lumen_cool", "Lumen — прохолодна"),
                    ("lumen_warm", "Lumen — тепла"),
                    ("soft_indigo", "Soft Indigo"),
                    ("soft_warm", "Soft Warm"),
                    ("dune_lite", "Dune Lite"),
                ],
                default="lumen_subtle",
                max_length=32,
                verbose_name="Theme",
            ),
        ),
    ]
