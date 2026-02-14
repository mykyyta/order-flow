from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.catalog.models import BundleColorMapping, BundleComponent, BundlePresetComponent
from apps.catalog.models import Product
from apps.catalog.variants import resolve_or_create_variant
from apps.inventory.domain import VariantId, WarehouseId
from apps.production.domain.status import STATUS_DONE
from apps.sales.domain.policies import resolve_line_production_status, resolve_sales_order_status
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineComponentSelection
from apps.warehouses.services import get_default_warehouse

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from apps.production.models import ProductionOrder


@transaction.atomic
def create_sales_order(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict[str, object]],
    notes: str = "",
    create_production_orders: bool = False,
    created_by: "AbstractBaseUser | None" = None,
    orders_url: str | None = None,
) -> SalesOrder:
    order = SalesOrder.objects.create(
        source=source,
        customer_info=customer_info,
        notes=notes,
    )

    for line_data in lines_data:
        product_id = int(line_data["product_id"])
        product = Product.objects.only("id", "kind").get(pk=product_id)
        if product.kind == Product.Kind.COMPONENT:
            raise ValueError(
                "Цей виріб не можна продавати окремо. Використай його як компонент комплекту."
            )
        variant_id = line_data.get("variant_id")
        if variant_id is None:
            variant = resolve_or_create_variant(
                product_id=product_id,
                color_id=line_data.get("color_id"),
                primary_material_color_id=line_data.get("primary_material_color_id"),
                secondary_material_color_id=line_data.get("secondary_material_color_id"),
            )
            variant_id = variant.id if variant else None

        line = SalesOrderLine.objects.create(
            sales_order=order,
            product_id=product_id,
            variant_id=variant_id,
            bundle_preset_id=line_data.get("bundle_preset_id"),
            quantity=int(line_data.get("quantity", 1)),
            production_mode=str(
                line_data.get("production_mode", SalesOrderLine.ProductionMode.AUTO)
            ),
        )

        if line.is_bundle:
            _save_bundle_component_variants(line=line, line_data=line_data)

    if create_production_orders:
        if created_by is None:
            raise ValueError("created_by is required when create_production_orders=True")
        create_production_orders_for_sales_order(
            sales_order=order,
            created_by=created_by,
            orders_url=orders_url,
        )

    return order


@transaction.atomic
def create_production_orders_for_sales_order(
    *,
    sales_order: SalesOrder,
    created_by: "AbstractBaseUser",
    orders_url: str | None = None,
) -> list["ProductionOrder"]:
    from apps.catalog.models import Variant
    from apps.inventory.services import get_stock_quantity
    from apps.production.services import create_production_order

    created_orders: list[ProductionOrder] = []
    available_stock_cache: dict[int, int] = {}
    warehouse_id = WarehouseId(get_default_warehouse().id)

    for line in sales_order.lines.select_related("product", "variant"):
        for variant_id, quantity_required in _iter_line_variant_requirements(line=line):
            quantity_to_produce = _resolve_quantity_to_produce(
                variant_id=variant_id,
                required_qty=quantity_required,
                warehouse_id=warehouse_id,
                available_stock_cache=available_stock_cache,
                get_stock_quantity_fn=get_stock_quantity,
            )
            variant = Variant.objects.select_related("product").get(id=variant_id)
            for _ in range(quantity_to_produce):
                created_orders.append(
                    create_production_order(
                        product=variant.product,
                        variant=variant,
                        is_embroidery=False,
                        is_urgent=False,
                        is_etsy=False,
                        comment=f"Sales order #{line.sales_order_id}, line #{line.id}",
                        created_by=created_by,
                        orders_url=orders_url,
                        sales_order_line=line,
                    )
                )

        sync_sales_order_line_production(line)

    _sync_sales_order_status(sales_order)
    return created_orders


def sync_sales_order_line_production(line: SalesOrderLine) -> None:
    total_orders = line.production_orders.count()
    finished_orders = line.production_orders.filter(status=STATUS_DONE).count()
    new_status = resolve_line_production_status(
        production_mode=line.production_mode,
        total_orders=total_orders,
        finished_orders=finished_orders,
    )

    if line.production_status != new_status:
        line.production_status = new_status
        line.save(update_fields=["production_status"])

    _sync_sales_order_status(line.sales_order)


def _save_bundle_component_variants(*, line: SalesOrderLine, line_data: dict[str, object]) -> None:
    if line.bundle_preset_id:
        preset_components = BundlePresetComponent.objects.filter(
            preset_id=line.bundle_preset_id
        ).select_related("component", "primary_material_color", "secondary_material_color")
        for preset_component in preset_components:
            variant = resolve_or_create_variant(
                product_id=preset_component.component_id,
                primary_material_color_id=preset_component.primary_material_color_id,
                secondary_material_color_id=preset_component.secondary_material_color_id,
            )
            SalesOrderLineComponentSelection.objects.create(
                order_line=line,
                component=preset_component.component,
                variant=variant,
            )
        return

    bundle_color_id = line_data.get("color_id")
    if bundle_color_id:
        mappings = BundleColorMapping.objects.filter(
            bundle_id=line.product_id,
            bundle_color_id=bundle_color_id,
        ).select_related("component", "component_color")
        for mapping in mappings:
            variant = resolve_or_create_variant(
                product_id=mapping.component_id,
                color_id=mapping.component_color_id,
            )
            SalesOrderLineComponentSelection.objects.create(
                order_line=line,
                component=mapping.component,
                variant=variant,
            )
        return

    component_variants = line_data.get("component_variants")
    if not component_variants:
        return

    for item in component_variants:
        if not isinstance(item, dict):
            continue
        component_id = int(item["component_id"])
        variant_id = item.get("variant_id")
        if variant_id is None:
            variant = resolve_or_create_variant(
                product_id=component_id,
                color_id=item.get("color_id"),
                primary_material_color_id=item.get("primary_material_color_id"),
                secondary_material_color_id=item.get("secondary_material_color_id"),
            )
            variant_id = variant.id if variant else None
        SalesOrderLineComponentSelection.objects.create(
            order_line=line,
            component_id=component_id,
            variant_id=variant_id,
        )


def _iter_line_variant_requirements(*, line: SalesOrderLine) -> list[tuple[int, int]]:
    if not line.is_bundle:
        if line.variant_id is None:
            raise ValueError("Sales order line requires variant")
        return [(line.variant_id, line.quantity)]

    selections = list(line.component_selections.select_related("component", "variant"))
    if not selections:
        raise ValueError("Bundle line requires component selections")

    quantities_by_component = {
        component_id: quantity
        for component_id, quantity in BundleComponent.objects.filter(
            bundle_id=line.product_id
        ).values_list("component_id", "quantity")
    }

    requirements: list[tuple[int, int]] = []
    for selection in selections:
        if selection.variant_id is None:
            raise ValueError("Bundle component selection requires variant")
        component_qty = quantities_by_component.get(selection.component_id, 1)
        requirements.append((selection.variant_id, line.quantity * component_qty))
    return requirements


def _resolve_quantity_to_produce(
    *,
    variant_id: int,
    required_qty: int,
    warehouse_id: WarehouseId,
    available_stock_cache: dict[int, int],
    get_stock_quantity_fn,
) -> int:
    available_qty = available_stock_cache.get(variant_id)
    if available_qty is None:
        available_qty = get_stock_quantity_fn(
            warehouse_id=warehouse_id,
            variant_id=VariantId(variant_id),
        )

    used_from_stock = min(required_qty, available_qty)
    available_stock_cache[variant_id] = available_qty - used_from_stock
    return required_qty - used_from_stock


def _sync_sales_order_status(sales_order: SalesOrder) -> None:
    lines = list(sales_order.lines.all())
    new_status = resolve_sales_order_status(
        status=sales_order.status,
        line_production_statuses=(line.production_status for line in lines),
    )
    if new_status is None:
        return

    sales_order.status = new_status
    sales_order.save(update_fields=["status", "updated_at"])
