"""Copy NotificationSetting rows from orders to accounts (same user_id)."""
from django.db import migrations


def copy_notification_settings(apps, schema_editor):
    OrderNotificationSetting = apps.get_model("orders", "NotificationSetting")
    AccountNotificationSetting = apps.get_model("accounts", "NotificationSetting")
    for old in OrderNotificationSetting.objects.all():
        AccountNotificationSetting.objects.get_or_create(
            user_id=old.user_id,
            defaults={
                "notify_order_created": old.notify_order_created,
                "notify_order_finished": old.notify_order_finished,
                "notify_order_created_pause": old.notify_order_created_pause,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_notificationsetting"),
        ("orders", "0012_remove_old_catalog_models"),
    ]

    operations = [
        migrations.RunPython(copy_notification_settings, noop_reverse),
    ]
