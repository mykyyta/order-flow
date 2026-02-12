from __future__ import annotations

import ast
from pathlib import Path

import pytest


DISALLOWED_MODULES = {
    "apps.orders",
    "apps.orders.models",
    "apps.orders.services",
    "apps.orders.forms",
    "apps.orders.views",
    "apps.orders.notifications",
    "apps.orders.legacy_import",
    "apps.orders.legacy_import_mappings",
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


@pytest.mark.django_db
def test_v2_apps_do_not_import_removed_orders_modules_directly():
    project_root = Path(__file__).resolve().parents[4]
    violations: list[str] = []

    for app_name in TARGET_APPS:
        app_dir = project_root / "src" / "apps" / app_name
        for py_file in app_dir.rglob("*.py"):
            rel_path = py_file.relative_to(project_root).as_posix()
            if "/tests/" in rel_path or "/migrations/" in rel_path:
                continue
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module
                    if module in DISALLOWED_MODULES or (module and module.startswith("apps.orders")):
                        violations.append(
                            f"{rel_path}:{node.lineno} has disallowed import-from {module}"
                        )
                if isinstance(node, ast.Import):
                    for imported in node.names:
                        if imported.name in DISALLOWED_MODULES or imported.name.startswith("apps.orders"):
                            violations.append(
                                f"{rel_path}:{node.lineno} has disallowed import {imported.name}"
                            )

    assert not violations, "Found forbidden imports:\n" + "\n".join(sorted(violations))
