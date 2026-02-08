"""Management command tests."""
import os
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_healthcheck_requires_tokens_when_flag_enabled():
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        with pytest.raises(CommandError):
            call_command("healthcheck_app", "--require-telegram-token")
