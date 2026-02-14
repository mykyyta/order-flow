from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("materials", "0006_alter_materialcolor_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderline",
            name="supplier_offer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchase_order_lines",
                to="materials.suppliermaterialoffer",
            ),
        ),
    ]

