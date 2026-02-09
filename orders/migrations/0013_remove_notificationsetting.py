from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0012_remove_old_catalog_models"),
        ("accounts", "0002_copy_notificationsetting_data"),
    ]

    operations = [
        migrations.DeleteModel(name="NotificationSetting"),
    ]
