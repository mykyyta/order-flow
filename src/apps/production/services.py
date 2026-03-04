"""Production order service layer: create and change status."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.catalog.variants import resolve_or_create_variant
from apps.inventory.domain import Quantity, VariantId, WarehouseId
from apps.warehouses.services import get_default_warehouse
from apps.production.notifications import send_order_created, send_order_finished
from apps.production.domain.status import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NEW, validate_status
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.catalog.models import Product, Variant
    from apps.materials.models import MaterialColor
    from apps.sales.models import SalesOrderLine


@transaction.atomic
def create_production_order(
    *,
    product: "Product",
    variant: "Variant | None" = None,
    primary_material_color: "MaterialColor | None" = None,
    secondary_material_color: "MaterialColor | None" = None,
    is_embroidery: bool,
    is_urgent: bool,
    is_etsy: bool,
    comment: str | None,
    created_by: "AbstractBaseUser",
    orders_url: str | None,
    sales_order_line: "SalesOrderLine | None" = None,
) -> ProductionOrder:
    if product.kind == product.Kind.BUNDLE:
        raise ValueError("Bundle products cannot be produced directly")
    if variant is None:
        requires_primary_color = bool(
            product.primary_material_id
            and product.primary_material.colors.filter(archived_at__isnull=True).exists()
        )
        if requires_primary_color and primary_material_color is None:
            raise ValueError("Order requires primary material color")
        if (
            primary_material_color is not None
            and product.primary_material_id is not None
            and primary_material_color.material_id != product.primary_material_id
        ):
            raise ValueError("Primary material color does not match product material")
        variant = resolve_or_create_variant(
            product_id=product.id,
            primary_material_color_id=primary_material_color.id if primary_material_color else None,
            secondary_material_color_id=secondary_material_color.id if secondary_material_color else None,
        )
    if variant is None:
        raise ValueError("Order requires resolvable variant")

    order = ProductionOrder.objects.create(
        product=product,
        variant=variant,
        is_embroidery=is_embroidery,
        is_urgent=is_urgent,
        is_etsy=is_etsy,
        comment=comment,
        status=STATUS_NEW,
        sales_order_line=sales_order_line,
    )
    ProductionOrderStatusHistory.objects.create(
        order=order,
        new_status=STATUS_NEW,
        changed_by=created_by,
    )

    send_order_created(order=order, orders_url=orders_url)
    return order


@transaction.atomic
def change_production_order_status(
    *,
    production_orders: list[ProductionOrder],
    new_status: str,
    changed_by: "AbstractBaseUser",
    on_order_done: Callable[[ProductionOrder, "AbstractBaseUser"], None] | None = None,
    on_sales_line_done: Callable[["SalesOrderLine"], None] | None = None,
) -> None:
    normalized = validate_status(new_status)
    order_done_handler = on_order_done or _add_finished_stock
    for order in production_orders:
        if normalized == STATUS_IN_PROGRESS:
            _consume_materials_for_order(order=order, changed_by=changed_by)
        order.transition_to(normalized, changed_by)
        order.save()
        if normalized == STATUS_DONE:
            order_done_handler(order, changed_by)
            if order.sales_order_line_id and on_sales_line_done is not None:
                on_sales_line_done(order.sales_order_line)

            send_order_finished(order=order)


def _add_finished_stock(
    order: ProductionOrder,
    changed_by: "AbstractBaseUser",
) -> None:
    from apps.inventory.models import ProductStockMovement
    from apps.inventory.services import add_to_stock

    warehouse_id = WarehouseId(get_default_warehouse().id)
    add_to_stock(
        warehouse_id=warehouse_id,
        variant_id=VariantId(order.variant_id),
        product_id=order.product_id,
        quantity=Quantity(1),
        reason=ProductStockMovement.Reason.PRODUCTION_IN,
        production_order=order,
        sales_order_line=order.sales_order_line,
        user=changed_by,
    )


def _consume_materials_for_order(*, order: ProductionOrder, changed_by: "AbstractBaseUser") -> None:
    if order.materials_consumed_at is not None:
        return
    if order.variant_id is None:
        raise ValueError("Order requires variant to consume materials")

    from apps.catalog.models import Variant
    from apps.materials.models import Material, MaterialColor, MaterialStockMovement
    from apps.materials.services import (
        calculate_material_requirements_for_variant,
        get_material_stock_quantity,
        remove_material_stock,
    )

    variant = Variant.objects.only(
        "id",
        "product_id",
        "primary_material_color_id",
        "secondary_material_color_id",
    ).get(id=order.variant_id)
    requirements = calculate_material_requirements_for_variant(variant=variant, quantity=1)
    if not requirements:
        return

    warehouse_id = get_default_warehouse().id
    material_ids = {r.material_id for r in requirements}
    color_ids = {r.material_color_id for r in requirements if r.material_color_id is not None}
    materials = Material.objects.in_bulk(material_ids)
    colors = MaterialColor.objects.in_bulk(color_ids) if color_ids else {}

    missing: list[str] = []
    for req in requirements:
        available = get_material_stock_quantity(
            warehouse_id=warehouse_id,
            material_id=req.material_id,
            material_color_id=req.material_color_id,
            unit=req.unit,
        )
        if available < req.quantity:
            material = materials.get(req.material_id)
            material_name = material.name if material else str(req.material_id)
            color_name = "-"
            if req.material_color_id is not None:
                color_name = colors.get(req.material_color_id).name if req.material_color_id in colors else "-"
            missing.append(
                f"{material_name} ({color_name}) є {available}, потрібно {req.quantity} {req.unit}"
            )

    if missing:
        raise ValueError("Недостатньо матеріалів: " + "; ".join(missing))

    for req in requirements:
        remove_material_stock(
            material=materials[req.material_id],
            material_color=colors.get(req.material_color_id) if req.material_color_id else None,
            quantity=req.quantity,
            unit=req.unit,
            reason=MaterialStockMovement.Reason.PRODUCTION_OUT,
            warehouse_id=warehouse_id,
            created_by=changed_by,
            notes=f"Production order #{order.id}",
        )

    order.materials_consumed_at = timezone.now()
    order.save(update_fields=["materials_consumed_at"])
