from __future__ import annotations

from typing import Final

DEFAULT_THEME: Final[str] = "lumen_subtle"

THEME_CHOICES: Final[list[tuple[str, str]]] = [
    ("lumen_subtle", "Lumen (Subtle)"),
    ("lumen_warm", "Lumen (Warm)"),
    ("lumen_night", "Lumen (Night)"),
    ("dune_lite", "Dune Lite"),
]

THEME_VALUES: Final[set[str]] = {value for value, _label in THEME_CHOICES}


def normalize_theme(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized in THEME_VALUES:
        return normalized
    dashed = normalized.replace("-", "_")
    if dashed in THEME_VALUES:
        return dashed
    return None
