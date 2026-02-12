from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.production.legacy_import import ImportMode, run_final_import_and_verify, run_import_legacy


class Command(BaseCommand):
    help = "Run legacy data import pipeline (dry-run, apply, verify)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate import inputs and show summary without writing data.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Execute import and persist changes.",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify imported aggregates and consistency.",
        )
        parser.add_argument(
            "--final",
            action="store_true",
            help="Run final apply + strict verify sequence.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail command when verify checks have issues.",
        )

    def handle(self, *args, **options):
        if options["final"]:
            if options["dry_run"] or options["apply"] or options["verify"]:
                raise CommandError("--final cannot be combined with --dry-run/--apply/--verify.")
            if options["strict"]:
                raise CommandError("--strict cannot be combined with --final.")

            result = run_final_import_and_verify()
            self.stdout.write(json.dumps(result, ensure_ascii=False))
            if result.get("result") != "ok":
                raise CommandError("Final import + verify failed.")
            return

        mode = self._resolve_mode(
            dry_run=options["dry_run"],
            apply=options["apply"],
            verify=options["verify"],
        )
        strict = options["strict"]
        if strict and mode != "verify":
            raise CommandError("--strict can be used only with --verify mode.")

        result = run_import_legacy(mode=mode, strict=strict)
        self.stdout.write(json.dumps(result, ensure_ascii=False))
        if strict and result.get("result") != "ok":
            raise CommandError("Legacy verify failed in strict mode.")

    def _resolve_mode(
        self,
        *,
        dry_run: bool,
        apply: bool,
        verify: bool,
    ) -> ImportMode:
        selected = [dry_run, apply, verify]
        if sum(selected) > 1:
            raise CommandError("Only one mode can be selected: --dry-run, --apply, or --verify.")
        if apply:
            return "apply"
        if verify:
            return "verify"
        return "dry-run"
