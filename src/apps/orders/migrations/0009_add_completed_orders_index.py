# Generated manually for performance

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0008_alter_order_current_status_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["current_status", "-finished_at"],
                name="orders_completed_idx",
            ),
        ),
    ]
