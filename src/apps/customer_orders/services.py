from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from django.db import transaction

from apps.catalog.models import BundleColorMapping, BundleComponent, BundlePresetComponent
from apps.catalog.variants import resolve_or_create_product_variant
from apps.customer_orders.models import CustomerOrder, CustomerOrderLine, CustomerOrderLineComponent
from apps.production.domain.status import STATUS_FINISHED

if TYPE_CHECKING:
    from apps.catalog.models import Color, ProductModel
    from apps.materials.models import MaterialColor
    from apps.orders.models import CustomUser, Order


Requirement = tuple[
    "ProductModel",
    int | None,
    "Color | None",
    "MaterialColor | None",
    "MaterialColor | None",
    int,
]


@transaction.atomic
def create_customer_order(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict[str, object]],
    notes: str = "",
    create_production_orders: bool = False,
    created_by: "CustomUser | None" = None,
    orders_url: str | None = None,
) -> CustomerOrder:
    order = CustomerOrder.objects.create(
        source=source,
        customer_info=customer_info,
        notes=notes,
    )

    for line_data in lines_data:
        line = CustomerOrderLine.objects.create(
            customer_order=order,
            product_model_id=int(line_data["product_model_id"]),
            color_id=line_data.get("color_id"),
            primary_material_color_id=line_data.get("primary_material_color_id"),
            secondary_material_color_id=line_data.get("secondary_material_color_id"),
            bundle_preset_id=line_data.get("bundle_preset_id"),
            quantity=int(line_data.get("quantity", 1)),
            production_mode=str(
                line_data.get("production_mode", CustomerOrderLine.ProductionMode.AUTO)
            ),
        )

        if line.is_bundle:
            _save_bundle_component_colors(line=line, line_data=line_data)
        else:
            _validate_line_material_colors(line=line)
            product_variant = resolve_or_create_product_variant(
                product_model_id=line.product_model_id,
                color_id=line.color_id,
                primary_material_color_id=line.primary_material_color_id,
                secondary_material_color_id=line.secondary_material_color_id,
            )
            if product_variant is not None and line.product_variant_id is None:
                line.product_variant = product_variant
                line.save(update_fields=["product_variant"])

    if create_production_orders:
        if created_by is None:
            raise ValueError("created_by is required when create_production_orders=True")
        create_missing_production_orders(
            customer_order=order,
            created_by=created_by,
            orders_url=orders_url,
        )

    return order


@transaction.atomic
def create_missing_production_orders(
    *,
    customer_order: CustomerOrder,
    created_by: "CustomUser",
    orders_url: str | None = None,
) -> list["Order"]:
    from apps.inventory.services import get_stock_quantity
    from apps.orders.services import create_order

    created_orders: list[Order] = []
    available_stock_cache: dict[tuple[str, int] | tuple[str, int, int | None, int | None, int | None], int] = {}

    for line in customer_order.lines.select_related(
        "product_model",
        "product_variant",
        "color",
        "primary_material_color",
        "secondary_material_color",
    ):
        for (
            product_model,
            product_variant_id,
            color,
            primary_color,
            secondary_color,
            required_qty,
        ) in _iter_line_requirements(
            line=line
        ):
            quantity_to_produce = _resolve_quantity_to_produce(
                line=line,
                product_model=product_model,
                product_variant_id=product_variant_id,
                color=color,
                primary_color=primary_color,
                secondary_color=secondary_color,
                required_qty=required_qty,
                available_stock_cache=available_stock_cache,
                get_stock_quantity_fn=get_stock_quantity,
            )
            for _ in range(quantity_to_produce):
                created_orders.append(
                    create_order(
                        model=product_model,
                        color=color,
                        primary_material_color=primary_color,
                        secondary_material_color=secondary_color,
                        embroidery=False,
                        urgent=False,
                        etsy=False,
                        comment=f"Customer order #{line.customer_order_id}, line #{line.id}",
                        created_by=created_by,
                        orders_url=orders_url,
                        customer_order_line=line,
                    )
                )

        sync_customer_order_line_production(line)

    _sync_customer_order_status(customer_order)
    return created_orders


def sync_customer_order_line_production(line: CustomerOrderLine) -> None:
    total_orders = line.production_orders.count()

    if total_orders == 0:
        if line.production_mode == CustomerOrderLine.ProductionMode.MANUAL:
            new_status = CustomerOrderLine.ProductionStatus.PENDING
        else:
            new_status = CustomerOrderLine.ProductionStatus.DONE
    else:
        finished_orders = line.production_orders.filter(current_status=STATUS_FINISHED).count()
        if finished_orders == 0:
            new_status = CustomerOrderLine.ProductionStatus.PENDING
        elif finished_orders < total_orders:
            new_status = CustomerOrderLine.ProductionStatus.IN_PROGRESS
        else:
            new_status = CustomerOrderLine.ProductionStatus.DONE

    if line.production_status != new_status:
        line.production_status = new_status
        line.save(update_fields=["production_status"])

    _sync_customer_order_status(line.customer_order)


def _save_bundle_component_colors(*, line: CustomerOrderLine, line_data: dict[str, object]) -> None:
    if line.bundle_preset_id:
        _save_bundle_preset_components(line=line)
        return

    if line.color_id:
        mappings = list(
            BundleColorMapping.objects.filter(
                bundle=line.product_model,
                bundle_color_id=line.color_id,
            ).select_related("component", "component_color")
        )
        if not mappings:
            raise ValueError("Bundle mapping is missing for selected bundle color")
        for mapping in mappings:
            CustomerOrderLineComponent.objects.create(
                order_line=line,
                component=mapping.component,
                color=mapping.component_color,
                product_variant=resolve_or_create_product_variant(
                    product_model_id=mapping.component_id,
                    color_id=mapping.component_color_id,
                ),
            )
        return

    component_colors = line_data.get("component_colors")
    if not component_colors:
        raise ValueError("Bundle line requires component colors")

    for component_data in component_colors:
        if not isinstance(component_data, dict):
            raise ValueError("Invalid component colors payload")
        component_line = CustomerOrderLineComponent.objects.create(
            order_line=line,
            component_id=int(component_data["component_id"]),
            color_id=component_data.get("color_id"),
            primary_material_color_id=component_data.get("primary_material_color_id"),
            secondary_material_color_id=component_data.get("secondary_material_color_id"),
        )
        _validate_component_material_colors(component_line)
        component_variant = resolve_or_create_product_variant(
            product_model_id=component_line.component_id,
            color_id=component_line.color_id,
            primary_material_color_id=component_line.primary_material_color_id,
            secondary_material_color_id=component_line.secondary_material_color_id,
        )
        if component_variant is not None and component_line.product_variant_id is None:
            component_line.product_variant = component_variant
            component_line.save(update_fields=["product_variant"])


def _save_bundle_preset_components(*, line: CustomerOrderLine) -> None:
    if line.bundle_preset is None:
        raise ValueError("Bundle preset is required")
    if line.bundle_preset.bundle_id != line.product_model_id:
        raise ValueError("Bundle preset does not match line bundle")

    preset_components = BundlePresetComponent.objects.filter(
        preset=line.bundle_preset
    ).select_related(
        "component",
        "primary_material_color",
        "secondary_material_color",
    )
    if not preset_components.exists():
        raise ValueError("Bundle preset has no components")

    for preset_component in preset_components:
        component_line = CustomerOrderLineComponent.objects.create(
            order_line=line,
            component=preset_component.component,
            primary_material_color=preset_component.primary_material_color,
            secondary_material_color=preset_component.secondary_material_color,
        )
        _validate_component_material_colors(component_line)
        component_variant = resolve_or_create_product_variant(
            product_model_id=component_line.component_id,
            color_id=component_line.color_id,
            primary_material_color_id=component_line.primary_material_color_id,
            secondary_material_color_id=component_line.secondary_material_color_id,
        )
        if component_variant is not None and component_line.product_variant_id is None:
            component_line.product_variant = component_variant
            component_line.save(update_fields=["product_variant"])


def _validate_line_material_colors(*, line: CustomerOrderLine) -> None:
    product = line.product_model

    if line.primary_material_color:
        if product.primary_material_id is None:
            raise ValueError("Product has no primary material")
        if line.primary_material_color.material_id != product.primary_material_id:
            raise ValueError("Selected primary material color does not match product primary material")
    elif line.color is None:
        raise ValueError("Non-bundle line requires color or primary material color")

    if line.secondary_material_color:
        if product.secondary_material_id is None:
            raise ValueError("Product has no secondary material")
        if line.secondary_material_color.material_id != product.secondary_material_id:
            raise ValueError("Selected secondary material color does not match product secondary material")


def _validate_component_material_colors(component_line: CustomerOrderLineComponent) -> None:
    component = component_line.component

    if component_line.primary_material_color:
        if component.primary_material_id is None:
            raise ValueError("Bundle component has no primary material")
        if component_line.primary_material_color.material_id != component.primary_material_id:
            raise ValueError("Selected primary material color does not match component primary material")
    elif component_line.color is None:
        raise ValueError("Bundle component requires color or primary material color")

    if component_line.secondary_material_color:
        if component.secondary_material_id is None:
            raise ValueError("Bundle component has no secondary material")
        if component_line.secondary_material_color.material_id != component.secondary_material_id:
            raise ValueError("Selected secondary material color does not match component secondary material")


def _iter_line_requirements(*, line: CustomerOrderLine) -> list[Requirement]:
    if not line.is_bundle:
        if line.color is None and line.primary_material_color is None:
            raise ValueError("Non-bundle line requires color or primary material color")
        return [
            (
                line.product_model,
                line.product_variant_id,
                line.color,
                line.primary_material_color,
                line.secondary_material_color,
                line.quantity,
            )
        ]

    components = list(
        line.component_colors.select_related(
            "component",
            "product_variant",
            "color",
            "primary_material_color",
            "secondary_material_color",
        )
    )
    if not components:
        raise ValueError("Bundle line requires component colors")

    quantities_by_component = {
        component_id: quantity
        for component_id, quantity in BundleComponent.objects.filter(
            bundle=line.product_model
        ).values_list("component_id", "quantity")
    }

    requirements: list[Requirement] = []
    for component in components:
        component_qty = quantities_by_component.get(component.component_id, 1)
        requirements.append(
            (
                component.component,
                component.product_variant_id,
                component.color,
                component.primary_material_color,
                component.secondary_material_color,
                line.quantity * component_qty,
            )
        )
    return requirements


def _resolve_quantity_to_produce(
    *,
    line: CustomerOrderLine,
    product_model: "ProductModel",
    product_variant_id: int | None,
    color: "Color | None",
    primary_color: "MaterialColor | None",
    secondary_color: "MaterialColor | None",
    required_qty: int,
    available_stock_cache: dict[tuple[str, int] | tuple[str, int, int | None, int | None, int | None], int],
    get_stock_quantity_fn: Callable[..., int],
) -> int:
    if line.production_mode == CustomerOrderLine.ProductionMode.FORCE:
        return required_qty
    if line.production_mode == CustomerOrderLine.ProductionMode.MANUAL:
        return 0

    if product_variant_id is not None:
        stock_key: tuple[str, int] | tuple[str, int, int | None, int | None, int | None] = (
            "variant",
            product_variant_id,
        )
    else:
        stock_key = (
            "legacy",
            product_model.id,
            color.id if color else None,
            primary_color.id if primary_color else None,
            secondary_color.id if secondary_color else None,
        )
    available_qty = available_stock_cache.get(stock_key)
    if available_qty is None:
        if product_variant_id is not None:
            available_qty = get_stock_quantity_fn(product_variant_id=product_variant_id)
        else:
            available_qty = get_stock_quantity_fn(
                product_model_id=product_model.id,
                color_id=color.id if color else None,
                primary_material_color_id=primary_color.id if primary_color else None,
                secondary_material_color_id=secondary_color.id if secondary_color else None,
            )

    used_from_stock = min(required_qty, available_qty)
    available_stock_cache[stock_key] = available_qty - used_from_stock
    return required_qty - used_from_stock


def _sync_customer_order_status(customer_order: CustomerOrder) -> None:
    terminal_statuses = {
        CustomerOrder.Status.SHIPPED,
        CustomerOrder.Status.COMPLETED,
        CustomerOrder.Status.CANCELLED,
    }
    if customer_order.status in terminal_statuses:
        return

    lines = list(customer_order.lines.all())
    if not lines:
        return

    if all(line.production_status == CustomerOrderLine.ProductionStatus.DONE for line in lines):
        new_status = CustomerOrder.Status.READY
    else:
        new_status = CustomerOrder.Status.PRODUCTION

    if customer_order.status != new_status:
        customer_order.status = new_status
        customer_order.save(update_fields=["status", "updated_at"])
