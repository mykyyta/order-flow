import pytest
from decimal import Decimal

from apps.catalog.models import Variant
from apps.catalog.tests.conftest import ColorFactory, ProductFactory
from apps.inventory.models import ProductStockMovement, ProductStock
from apps.materials.models import Material, MaterialStockMovement, MaterialStock, MaterialUnit
from apps.production.legacy_import import run_final_import_and_verify, run_import_legacy
from apps.production.legacy_import_mappings import (
    LEGACY_FINISHED_MOVEMENT_REASON_TO_V2,
    LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2,
    LEGACY_ORDER_STATUS_TO_V2,
)
from apps.production.models import ProductionOrderStatusHistory
from apps.production.tests.factories import OrderFactory
from apps.warehouses.models import Warehouse


def test_legacy_order_status_mapping_handles_almost_finished():
    assert LEGACY_ORDER_STATUS_TO_V2["almost_finished"] == "done"


def test_legacy_movement_reason_mappings_contain_core_values():
    assert LEGACY_FINISHED_MOVEMENT_REASON_TO_V2["production_in"] == "production_in"
    assert LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2["purchase_in"] == "purchase_in"


@pytest.mark.django_db
def test_dry_run_reports_pending_updates_without_writing():
    order = OrderFactory(status="almost_finished")
    ProductionOrderStatusHistory.objects.create(
        order=order,
        changed_by=None,
        new_status="almost_finished",
    )

    result = run_import_legacy(mode="dry-run")

    order.refresh_from_db()
    assert order.status == "almost_finished"
    assert result["pending_updates"]["order_statuses"] >= 1
    assert result["pending_updates"]["order_status_history"] >= 1


@pytest.mark.django_db
def test_verify_mode_returns_mapping_summary():
    result = run_import_legacy(mode="verify")

    assert result["mode"] == "verify"
    assert result["result"] == "ok"
    assert result["mappings"]["order_statuses"] > 0
    assert result["mappings"]["finished_movement_reasons"] > 0
    assert result["mappings"]["material_movement_reasons"] > 0


@pytest.mark.django_db
def test_verify_mode_returns_aggregate_snapshot():
    result = run_import_legacy(mode="verify")

    assert result["aggregates"]["orders"] >= 0
    assert result["aggregates"]["sales_orders"] >= 0
    assert result["aggregates"]["sales_order_lines"] >= 0
    assert result["aggregates"]["variants"] >= 0
    assert result["aggregates"]["finished_stock_records"] >= 0
    assert result["aggregates"]["material_stock_records"] >= 0
    assert result["aggregates"]["finished_stock_quantity_total"] >= 0
    assert isinstance(result["aggregates"]["finished_movement_net_total"], int)
    assert isinstance(result["aggregates"]["finished_balance_delta"], int)
    Decimal(result["aggregates"]["material_stock_quantity_total"])
    Decimal(result["aggregates"]["material_movement_net_total"])
    Decimal(result["aggregates"]["material_balance_delta"])


@pytest.mark.django_db
def test_verify_mode_returns_finished_balance_by_warehouse():
    warehouse = Warehouse.objects.create(
        name="Verify Finished Warehouse",
        code="VRF-FIN",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    product = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=product, color=color)
    stock_record = ProductStock.objects.create(
        warehouse=warehouse,
        variant=variant,
        quantity=5,
    )
    ProductStockMovement.objects.create(
        stock_record=stock_record,
        quantity_change=4,
        reason=ProductStockMovement.Reason.ADJUSTMENT_IN,
    )

    result = run_import_legacy(mode="verify")
    rows = result["aggregates"]["finished_balances_by_warehouse"]
    row = next(item for item in rows if item["warehouse_code"] == "VRF-FIN")
    assert row["stock_total"] == 5
    assert row["movement_net_total"] == 4
    assert row["delta"] == 1


@pytest.mark.django_db
def test_verify_mode_returns_material_balance_by_warehouse_and_unit():
    warehouse = Warehouse.objects.create(
        name="Verify Material Warehouse",
        code="VRF-MAT",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    material = Material.objects.create(name="Verify Leather")
    stock_record = MaterialStock.objects.create(
        warehouse=warehouse,
        material=material,
        unit=MaterialUnit.PIECE,
        quantity=Decimal("2.500"),
    )
    MaterialStockMovement.objects.create(
        stock_record=stock_record,
        quantity_change=Decimal("1.250"),
        reason=MaterialStockMovement.Reason.ADJUSTMENT_IN,
    )

    result = run_import_legacy(mode="verify")
    rows = result["aggregates"]["material_balances_by_warehouse_unit"]
    row = next(
        item
        for item in rows
        if item["warehouse_code"] == "VRF-MAT" and item["unit"] == MaterialUnit.PIECE
    )
    assert row["stock_total"] == "2.500"
    assert row["movement_net_total"] == "1.250"
    assert row["delta"] == "1.250"


@pytest.mark.django_db
def test_apply_mode_normalizes_legacy_order_statuses():
    order = OrderFactory(status="almost_finished")
    ProductionOrderStatusHistory.objects.create(
        order=order,
        changed_by=None,
        new_status="almost_finished",
    )

    result = run_import_legacy(mode="apply")

    order.refresh_from_db()
    history_status = order.history.latest("id").new_status
    assert order.status == "done"
    assert history_status == "done"
    assert result["updated"]["order_statuses"] >= 1
    assert result["updated"]["order_status_history"] >= 1


@pytest.mark.django_db
def test_verify_mode_strict_fails_when_deltas_are_non_zero():
    warehouse = Warehouse.objects.create(
        name="Strict Verify Warehouse",
        code="VRF-STRICT",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    product = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=product, color=color)
    ProductStock.objects.create(
        warehouse=warehouse,
        variant=variant,
        quantity=1,
    )

    result = run_import_legacy(mode="verify", strict=True)

    assert result["result"] == "failed"
    assert result["checks"]["passed"] is False
    assert any(issue["code"] == "finished_balance_delta" for issue in result["checks"]["issues"])
    assert any(issue["code"] == "finished_balance_by_warehouse" for issue in result["checks"]["issues"])


@pytest.mark.django_db
def test_verify_mode_reports_unknown_values():
    order = OrderFactory(status="new")
    ProductionOrderStatusHistory.objects.create(
        order=order,
        changed_by=None,
        new_status="mystery_status",
    )

    result = run_import_legacy(mode="verify")

    assert "mystery_status" in result["unknown_values"]["order_status_history"]
    assert any(issue["code"] == "unknown_order_status_history" for issue in result["checks"]["issues"])


@pytest.mark.django_db
def test_run_final_import_and_verify_normalizes_statuses_and_succeeds():
    order = OrderFactory(status="almost_finished")
    ProductionOrderStatusHistory.objects.create(
        order=order,
        changed_by=None,
        new_status="almost_finished",
    )

    result = run_final_import_and_verify()

    order.refresh_from_db()
    assert order.status == "done"
    assert result["mode"] == "final"
    assert result["apply"]["mode"] == "apply"
    assert result["verify"]["mode"] == "verify"
    assert result["result"] == "ok"


@pytest.mark.django_db
def test_run_final_import_and_verify_fails_when_verify_checks_fail():
    warehouse = Warehouse.objects.create(
        name="Final Verify Warehouse",
        code="VRF-FINAL",
        kind=Warehouse.Kind.STORAGE,
        is_default_for_production=False,
        is_active=True,
    )
    product = ProductFactory(kind="standard")
    color = ColorFactory()
    variant = Variant.objects.create(product=product, color=color)
    ProductStock.objects.create(
        warehouse=warehouse,
        variant=variant,
        quantity=1,
    )

    result = run_final_import_and_verify()

    assert result["result"] == "failed"
    assert result["verify"]["result"] == "failed"
