from __future__ import annotations

from apps.catalog.models import Variant


def resolve_or_create_variant(
    *,
    product_id: int,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> Variant | None:
    if secondary_material_color_id is not None and primary_material_color_id is None:
        return None

    if color_id is not None:
        if primary_material_color_id is not None or secondary_material_color_id is not None:
            return None
        variant, _ = Variant.objects.get_or_create(
            product_id=product_id,
            color_id=color_id,
            primary_material_color_id=None,
            secondary_material_color_id=None,
            defaults={"is_active": True},
        )
        return variant

    if primary_material_color_id is None:
        variant, _ = Variant.objects.get_or_create(
            product_id=product_id,
            color_id=None,
            primary_material_color_id=None,
            secondary_material_color_id=None,
            defaults={"is_active": True},
        )
        return variant

    variant, _ = Variant.objects.get_or_create(
        product_id=product_id,
        color_id=None,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
        defaults={"is_active": True},
    )
    return variant
