from django.db import migrations, models


def dedupe_purchase_request_lines(apps, schema_editor):
    PurchaseRequestLine = apps.get_model("materials", "PurchaseRequestLine")

    # Keep the earliest line per request and delete the rest.
    seen = set()
    for line in PurchaseRequestLine.objects.order_by("request_id", "id").only("id", "request_id"):
        if line.request_id in seen:
            PurchaseRequestLine.objects.filter(pk=line.pk).delete()
        else:
            seen.add(line.request_id)


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0007_purchaseorderline_supplier_offer"),
    ]

    operations = [
        migrations.RunPython(dedupe_purchase_request_lines, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="purchaserequestline",
            constraint=models.UniqueConstraint(
                fields=("request",),
                name="materials_purchaserequestline_one_line_per_request",
            ),
        ),
    ]

