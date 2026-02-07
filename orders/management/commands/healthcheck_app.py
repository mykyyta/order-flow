from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Healthcheck for DB connectivity and required settings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-telegram-token",
            action="store_true",
            help="Fail when TELEGRAM_BOT_TOKEN is missing.",
        )
        parser.add_argument(
            "--require-delayed-token",
            action="store_true",
            help="Fail when DELAYED_NOTIFICATIONS_TOKEN is missing.",
        )

    def handle(self, *args, **options):
        self._check_database()
        self._check_env(
            require_telegram_token=options["require_telegram_token"],
            require_delayed_token=options["require_delayed_token"],
        )
        self.stdout.write(self.style.SUCCESS("ok"))

    def _check_database(self) -> None:
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"database check failed: {exc}") from exc

    def _check_env(
        self,
        *,
        require_telegram_token: bool,
        require_delayed_token: bool,
    ) -> None:
        missing = []

        if require_telegram_token and not os.getenv("TELEGRAM_BOT_TOKEN"):
            missing.append("TELEGRAM_BOT_TOKEN")

        if require_delayed_token and not os.getenv("DELAYED_NOTIFICATIONS_TOKEN"):
            missing.append("DELAYED_NOTIFICATIONS_TOKEN")

        if missing:
            raise CommandError(f"missing env vars: {', '.join(missing)}")
