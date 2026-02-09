from __future__ import annotations

from apps.catalog.models import ProductVariant


def product_variant_matches_legacy_fields(
    *,
    product_variant: ProductVariant | None,
    product_model_id: int,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> bool:
    if product_variant is None:
        return True

    return (
        product_variant.product_id == product_model_id
        and product_variant.color_id == color_id
        and product_variant.primary_material_color_id == primary_material_color_id
        and product_variant.secondary_material_color_id == secondary_material_color_id
    )


def resolve_or_create_product_variant(
    *,
    product_model_id: int,
    color_id: int | None = None,
    primary_material_color_id: int | None = None,
    secondary_material_color_id: int | None = None,
) -> ProductVariant | None:
    if color_id is not None:
        if primary_material_color_id is not None or secondary_material_color_id is not None:
            return None
        variant, _ = ProductVariant.objects.get_or_create(
            product_id=product_model_id,
            color_id=color_id,
            primary_material_color_id=None,
            secondary_material_color_id=None,
            defaults={"is_active": True},
        )
        return variant

    if primary_material_color_id is None:
        return None

    variant, _ = ProductVariant.objects.get_or_create(
        product_id=product_model_id,
        color_id=None,
        primary_material_color_id=primary_material_color_id,
        secondary_material_color_id=secondary_material_color_id,
        defaults={"is_active": True},
    )
    return variant
