from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set, Tuple

STATUS_NEW = "new"
STATUS_DOING = "doing"
STATUS_EMBROIDERY = "embroidery"
STATUS_DECIDING = "deciding"
STATUS_ON_HOLD = "on_hold"
STATUS_FINISHED = "finished"
STATUS_ALMOST_FINISHED = "almost_finished"


@dataclass(frozen=True)
class OrderStatusDefinition:
    code: str
    label: str
    icon: str
    indicator_class: str
    text_class: str
    badge_class: str
    is_terminal: bool = False
    is_legacy: bool = False


STATUS_DEFINITIONS: Tuple[OrderStatusDefinition, ...] = (
    OrderStatusDefinition(
        code=STATUS_NEW,
        label="Нове",
        icon="dot",
        indicator_class="text-emerald-600",
        text_class="text-slate-700",
        badge_class="bg-emerald-100 text-emerald-800",
    ),
    OrderStatusDefinition(
        code=STATUS_DOING,
        label="Робимо",
        icon="play",
        indicator_class="text-blue-500",
        text_class="text-slate-700",
        badge_class="bg-blue-100 text-blue-800",
    ),
    OrderStatusDefinition(
        code=STATUS_EMBROIDERY,
        label="Вишиваємо",
        icon="play",
        indicator_class="text-blue-500",
        text_class="text-slate-700",
        badge_class="bg-blue-100 text-blue-800",
    ),
    OrderStatusDefinition(
        code=STATUS_DECIDING,
        label="Рішаємо",
        icon="pause",
        indicator_class="text-amber-600",
        text_class="text-slate-700",
        badge_class="bg-amber-100 text-amber-800",
    ),
    OrderStatusDefinition(
        code=STATUS_ON_HOLD,
        label="Чогось нема",
        icon="pause",
        indicator_class="text-orange-500",
        text_class="text-slate-700",
        badge_class="bg-orange-100 text-orange-800",
    ),
    OrderStatusDefinition(
        code=STATUS_FINISHED,
        label="Фініш",
        icon="none",
        indicator_class="text-slate-400",
        text_class="text-slate-500",
        badge_class="bg-slate-100 text-slate-700",
        is_terminal=True,
    ),
    OrderStatusDefinition(
        code=STATUS_ALMOST_FINISHED,
        label="Майже готове",
        icon="dot",
        indicator_class="text-emerald-600",
        text_class="text-slate-500",
        badge_class="bg-slate-100 text-slate-700",
        is_legacy=True,
    ),
)

STATUS_BY_CODE: Dict[str, OrderStatusDefinition] = {
    status.code: status for status in STATUS_DEFINITIONS
}
ALL_STATUS_CODES: Tuple[str, ...] = tuple(status.code for status in STATUS_DEFINITIONS)
ACTIVE_STATUS_CODES: Tuple[str, ...] = tuple(
    status.code for status in STATUS_DEFINITIONS if not status.is_legacy
)
LEGACY_STATUS_CODES: Tuple[str, ...] = tuple(
    status.code for status in STATUS_DEFINITIONS if status.is_legacy
)
TERMINAL_STATUS_CODES: Tuple[str, ...] = tuple(
    status.code for status in STATUS_DEFINITIONS if status.is_terminal
)

# Порядок у списку поточних замовлень: нові → робимо/вишиваємо → рішаємо → чогось нема
ACTIVE_LIST_ORDER: Tuple[str, ...] = (
    STATUS_NEW,
    STATUS_DOING,
    STATUS_EMBROIDERY,
    STATUS_DECIDING,
    STATUS_ON_HOLD,
)


def status_choices(*, include_legacy: bool, include_terminal: bool) -> Tuple[Tuple[str, str], ...]:
    choices = []
    for status in STATUS_DEFINITIONS:
        if not include_legacy and status.is_legacy:
            continue
        if not include_terminal and status.is_terminal:
            continue
        choices.append((status.code, status.label))
    return tuple(choices)


def status_choices_for_active_page() -> Tuple[Tuple[str, str], ...]:
    """Choices for bulk status change on active orders page. Excludes 'new' as it is forbidden."""
    return tuple(
        (code, label)
        for code, label in status_choices(include_legacy=False, include_terminal=True)
        if code != STATUS_NEW
    )


def status_label_map(*, include_legacy: bool) -> Dict[str, str]:
    return dict(status_choices(include_legacy=include_legacy, include_terminal=True))


def status_ui_map(*, include_legacy: bool) -> Dict[str, Dict[str, str]]:
    ui = {}
    for status in STATUS_DEFINITIONS:
        if not include_legacy and status.is_legacy:
            continue
        ui[status.code] = {
            "dot_class": status.indicator_class,
            "icon": status.icon,
            "text_class": status.text_class,
            "badge_class": status.badge_class,
        }
    return ui


def get_allowed_transitions(current_status: str) -> Set[str]:
    current = STATUS_BY_CODE.get(current_status)
    if current is None or current.is_terminal:
        return set()

    allowed = {
        status.code
        for status in STATUS_DEFINITIONS
        if not status.is_legacy and not status.is_terminal
    }
    allowed.add(STATUS_FINISHED)
    allowed.discard(current_status)
    if current_status != STATUS_NEW:
        allowed.discard(STATUS_NEW)
    return allowed


def transition_map(*, include_legacy_current: bool) -> Dict[str, Set[str]]:
    statuses = (
        STATUS_DEFINITIONS
        if include_legacy_current
        else tuple(status for status in STATUS_DEFINITIONS if not status.is_legacy)
    )
    return {status.code: get_allowed_transitions(status.code) for status in statuses}
