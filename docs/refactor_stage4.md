# Рефакторинг: Етап 4 (2026-02-07)

## Ціль етапу
Винести відкладені нотифікації у background‑виконання через management command.

## План етапу
1. Додати management command для відкладених нотифікацій.
2. Залишити HTTP endpoint як thin wrapper (опційно для ручного виклику).

## Реалізація (виконано)
- Додано management command:
  - `orders/management/commands/send_delayed_notifications.py`.

## Як запускати
```
python manage.py send_delayed_notifications
```

## Наступні кроки
- Додати правила переходів статусів.
- Розглянути `Order.current_status` для оптимізації списків.
- Додати логування відправлених нотифікацій.
