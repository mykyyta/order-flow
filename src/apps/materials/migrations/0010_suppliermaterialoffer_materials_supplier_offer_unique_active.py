from django.db import migrations, models


def archive_duplicate_offers(apps, schema_editor) -> None:
    from django.db.models import Count, Max
    from django.utils import timezone

    Offer = apps.get_model("materials", "SupplierMaterialOffer")
    duplicates = (
        Offer.objects.filter(archived_at__isnull=True)
        .values("supplier_id", "material_id", "material_color_id", "unit")
        .annotate(cnt=Count("id"), keep_id=Max("id"))
        .filter(cnt__gt=1)
    )
    now = timezone.now()
    for row in duplicates:
        Offer.objects.filter(
            supplier_id=row["supplier_id"],
            material_id=row["material_id"],
            material_color_id=row["material_color_id"],
            unit=row["unit"],
            archived_at__isnull=True,
        ).exclude(id=row["keep_id"]).update(archived_at=now, updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0009_alter_materialstockmovement_reason'),
    ]

    operations = [
        migrations.RunPython(archive_duplicate_offers, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='suppliermaterialoffer',
            constraint=models.UniqueConstraint(condition=models.Q(('archived_at__isnull', True)), fields=('supplier', 'material', 'material_color', 'unit'), name='materials_supplier_offer_unique_active'),
        ),
    ]
