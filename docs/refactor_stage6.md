# Рефакторинг: Етап 6 (2026-02-07)

## Ціль етапу
Оптимізувати читання статусів через поле `Order.current_status`, зберігаючи історію статусів.

## План етапу
1. Додати поле `current_status` та міграцію з backfill.
2. Оновити `OrderService` і репозиторій, щоб підтримувати поле.
3. Додати/оновити тести.

## Реалізація (виконано)
- Додано поле `current_status`:
  - `orders/models.py`.
- Міграція з backfill:
  - `orders/migrations/0005_order_current_status.py`.
- Підтримка в сервісі та репозиторії:
  - `orders/application/order_service.py`, `orders/adapters/orders_repository.py`.
- Оновлені тести:
  - `orders/tests.py`.

## Як застосувати
```
python manage.py migrate
```

## Примітки
- Статуси в `OrderStatusHistory` та `Order` узгоджені через доменні константи.
- Якщо потрібен інший порядок переходів, їх можна змінити в `orders/domain/transitions.py`.
