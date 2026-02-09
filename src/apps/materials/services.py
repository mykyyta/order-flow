from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.catalog.models import BundleComponent
from apps.customer_orders.models import CustomerOrderLine
from apps.materials.models import ProductMaterial


@dataclass(frozen=True)
class MaterialRequirement:
    material_id: int
    material_name: str
    unit: str
    quantity: Decimal


def calculate_material_requirements_for_customer_order_line(
    *,
    line: CustomerOrderLine,
) -> list[MaterialRequirement]:
    totals: dict[tuple[int, str], Decimal] = {}
    labels: dict[int, str] = {}

    for product_model_id, produced_quantity in _iter_line_product_quantities(line=line):
        for norm in ProductMaterial.objects.filter(product_model_id=product_model_id).select_related(
            "material"
        ):
            key = (norm.material_id, norm.unit)
            quantity = norm.quantity_per_unit * produced_quantity
            totals[key] = totals.get(key, Decimal("0")) + quantity
            labels[norm.material_id] = norm.material.name

    requirements = [
        MaterialRequirement(
            material_id=material_id,
            material_name=labels[material_id],
            unit=unit,
            quantity=quantity.quantize(Decimal("0.01")),
        )
        for (material_id, unit), quantity in totals.items()
    ]
    return sorted(requirements, key=lambda item: item.material_name)


def _iter_line_product_quantities(*, line: CustomerOrderLine) -> list[tuple[int, Decimal]]:
    if not line.is_bundle:
        return [(line.product_model_id, Decimal(line.quantity))]

    bundle_components = BundleComponent.objects.filter(bundle_id=line.product_model_id)
    return [
        (component.component_id, Decimal(line.quantity * component.quantity))
        for component in bundle_components
    ]
