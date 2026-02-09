"""Management command tests."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_healthcheck_requires_tokens_when_flag_enabled():
    with pytest.raises(CommandError):
        call_command("healthcheck_app", "--require-telegram-token")
