from django.db import migrations, models


def _normalize_user_themes(apps, schema_editor) -> None:
    CustomUser = apps.get_model("orders", "CustomUser")

    allowed = {"lumen_subtle", "lumen_warm", "lumen_night", "dune_lite"}
    CustomUser.objects.exclude(theme__in=allowed).update(theme="lumen_subtle")


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0016_customuser_theme_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="theme",
            field=models.CharField(
                choices=[
                    ("lumen_subtle", "Lumen (Subtle)"),
                    ("lumen_warm", "Lumen (Warm)"),
                    ("lumen_night", "Lumen (Night)"),
                    ("dune_lite", "Dune Lite"),
                ],
                default="lumen_subtle",
                max_length=32,
                verbose_name="Theme",
            ),
        ),
        migrations.RunPython(_normalize_user_themes, migrations.RunPython.noop),
    ]
