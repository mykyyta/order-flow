from __future__ import annotations

import ast
from pathlib import Path

import pytest


DISALLOWED_MODULES = {
    "apps.orders.models",
    "apps.orders.services",
    "apps.customer_orders.models",
    "apps.customer_orders.services",
}
TARGET_APPS = (
    "sales",
    "production",
    "fulfillment",
    "product_inventory",
    "inventory",
    "procurement",
    "material_inventory",
)
ALLOWED_COMPATIBILITY_FILES = {
    "src/apps/sales/models.py",
    "src/apps/sales/services.py",
    "src/apps/production/models.py",
    "src/apps/production/services.py",
}


@pytest.mark.django_db
def test_v2_apps_do_not_import_legacy_orders_customer_orders_modules_directly():
    project_root = Path(__file__).resolve().parents[4]
    violations: list[str] = []

    for app_name in TARGET_APPS:
        app_dir = project_root / "src" / "apps" / app_name
        for py_file in app_dir.rglob("*.py"):
            rel_path = py_file.relative_to(project_root).as_posix()
            if "/tests/" in rel_path or "/migrations/" in rel_path:
                continue
            if rel_path in ALLOWED_COMPATIBILITY_FILES:
                continue

            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module
                    if module in DISALLOWED_MODULES:
                        violations.append(
                            f"{rel_path}:{node.lineno} has disallowed import-from {module}"
                        )
                if isinstance(node, ast.Import):
                    for imported in node.names:
                        if imported.name in DISALLOWED_MODULES:
                            violations.append(
                                f"{rel_path}:{node.lineno} has disallowed import {imported.name}"
                            )

    assert not violations, "Found forbidden imports:\n" + "\n".join(sorted(violations))
