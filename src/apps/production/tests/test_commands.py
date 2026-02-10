"""Management command tests."""
import os
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import Color, Product
from apps.production.domain.status import STATUS_DONE
from apps.production.models import ProductionOrder, ProductionOrderStatusHistory


@pytest.mark.django_db
def test_healthcheck_requires_tokens_when_flag_enabled():
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        with pytest.raises(CommandError):
            call_command("healthcheck_app", "--require-telegram-token")


@pytest.mark.django_db
def test_import_legacy_defaults_to_dry_run_mode():
    output = StringIO()
    with patch("apps.production.management.commands.import_legacy.run_import_legacy") as run_import:
        run_import.return_value = {"mode": "dry-run", "result": "ok"}
        call_command("import_legacy", stdout=output)

    run_import.assert_called_once_with(mode="dry-run", strict=False)
    assert "dry-run" in output.getvalue()


@pytest.mark.django_db
def test_import_legacy_apply_mode():
    output = StringIO()
    with patch("apps.production.management.commands.import_legacy.run_import_legacy") as run_import:
        run_import.return_value = {"mode": "apply", "result": "ok"}
        call_command("import_legacy", "--apply", stdout=output)

    run_import.assert_called_once_with(mode="apply", strict=False)
    assert "apply" in output.getvalue()


@pytest.mark.django_db
def test_import_legacy_verify_mode():
    output = StringIO()
    with patch("apps.production.management.commands.import_legacy.run_import_legacy") as run_import:
        run_import.return_value = {"mode": "verify", "result": "ok"}
        call_command("import_legacy", "--verify", stdout=output)

    run_import.assert_called_once_with(mode="verify", strict=False)
    assert "verify" in output.getvalue()


@pytest.mark.django_db
def test_import_legacy_rejects_multiple_modes():
    with pytest.raises(CommandError, match="Only one mode"):
        call_command("import_legacy", "--apply", "--verify")


@pytest.mark.django_db
def test_import_legacy_rejects_strict_without_verify():
    with pytest.raises(CommandError, match="only with --verify"):
        call_command("import_legacy", "--strict")


@pytest.mark.django_db
def test_import_legacy_strict_verify_fails_on_failed_result():
    output = StringIO()
    with patch("apps.production.management.commands.import_legacy.run_import_legacy") as run_import:
        run_import.return_value = {"mode": "verify", "result": "failed"}
        with pytest.raises(CommandError, match="strict mode"):
            call_command("import_legacy", "--verify", "--strict", stdout=output)

    run_import.assert_called_once_with(mode="verify", strict=True)


@pytest.mark.django_db
def test_import_legacy_final_mode():
    output = StringIO()
    with patch(
        "apps.production.management.commands.import_legacy.run_final_import_and_verify"
    ) as run_final_import:
        run_final_import.return_value = {"mode": "final", "result": "ok"}
        call_command("import_legacy", "--final", stdout=output)

    run_final_import.assert_called_once_with()
    assert "final" in output.getvalue()


@pytest.mark.django_db
def test_import_legacy_rejects_final_with_modes():
    with pytest.raises(CommandError, match="cannot be combined"):
        call_command("import_legacy", "--final", "--verify")


@pytest.mark.django_db
def test_import_legacy_rejects_strict_with_final():
    with pytest.raises(CommandError, match="cannot be combined"):
        call_command("import_legacy", "--final", "--strict")


@pytest.mark.django_db
def test_generate_sample_orders_creates_orders_with_variants_and_history():
    call_command("generate_sample_orders", "--count", "3")

    orders = list(ProductionOrder.objects.select_related("product", "variant"))
    assert len(orders) == 3
    assert all(order.product_id is not None for order in orders)
    assert all(order.variant_id is not None for order in orders)
    assert ProductionOrderStatusHistory.objects.count() == 3


@pytest.mark.django_db
def test_generate_sample_orders_sets_finished_at_for_done_orders():
    call_command("generate_sample_orders", "--count", "30")

    done_orders = ProductionOrder.objects.filter(status=STATUS_DONE)
    assert done_orders.exists()
    assert done_orders.filter(finished_at__isnull=True).count() == 0


@pytest.mark.django_db
def test_bootstrap_local_creates_admin_user_and_catalog():
    call_command(
        "bootstrap_local",
        "--username",
        "local_tester",
        "--password",
        "local-pass-12345",
        "--orders",
        "0",
    )

    user = get_user_model().objects.get(username="local_tester")
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password("local-pass-12345")
    assert Product.objects.exists()
    assert Color.objects.exists()
