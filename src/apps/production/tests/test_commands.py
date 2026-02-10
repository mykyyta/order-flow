"""Management command tests."""
import os
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


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
