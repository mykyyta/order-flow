# Generated manually

from django.db import migrations, models


def _normalize_product_sections(apps, schema_editor) -> None:
    Product = apps.get_model("catalog", "Product")

    for product in Product.objects.all().only("id", "section"):
        raw = (product.section or "").strip()
        low = raw.lower()

        if not low:
            normalized = ""
        elif low in {"bags", "bag", "сумки", "сумка"}:
            normalized = "bags"
        elif low in {"accessories", "accessory", "аксесуари", "аксессуари", "аксесуар"}:
            normalized = "accessories"
        elif low in {"cases", "case", "чохли", "чохол"}:
            normalized = "cases"
        else:
            # Strict: unknown sections are not allowed, reset to blank.
            normalized = ""

        if product.section != normalized:
            product.section = normalized
            product.save(update_fields=["section"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_product_allows_embroidery"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="section",
            field=models.CharField(
                blank=True,
                choices=[("bags", "Сумки"), ("accessories", "Аксесуари"), ("cases", "Чохли")],
                db_index=True,
                max_length=255,
            ),
        ),
        migrations.RunPython(_normalize_product_sections, reverse_code=migrations.RunPython.noop),
    ]

