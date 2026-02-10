from __future__ import annotations

from django.conf import settings


class LegacyWritesFrozenError(RuntimeError):
    pass


def ensure_legacy_writes_allowed(*, operation: str, via_v2_context: bool) -> None:
    if via_v2_context:
        return
    if settings.FREEZE_LEGACY_WRITES:
        raise LegacyWritesFrozenError(
            f"Legacy writes are frozen for `{operation}`. Use V2 context service entrypoints."
        )
