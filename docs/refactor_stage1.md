# Рефакторинг: Етап 1 (запущено 2026-02-07)

## Ціль етапу
Створити перший «шар» гексагональної архітектури без зміни поведінки: винести бізнес-логіку зі `views.py` у прикладний сервіс, додати порти/адаптери та підготувати основу для DDD.

## План етапу
1. Ввести доменні політики (мінімально) без залежності від Django.
2. Описати порти (`OrderRepository`, `NotificationSender`, `Clock`).
3. Реалізувати прикладний сервіс `OrderService`.
4. Додати адаптери Django ORM і Telegram.
5. Перепідключити `views.py` на сервіс.

## Реалізація (виконано)
- Додані доменні політики:
  - `orders/domain/policies.py` (логіка `finished_at` за статусом).
- Додані порти прикладного рівня:
  - `orders/application/ports.py`.
- Доданий прикладний сервіс:
  - `orders/application/order_service.py`.
- Додані адаптери:
  - `orders/adapters/orders_repository.py` (ORM доступ).
  - `orders/adapters/notifications.py` (Telegram + правила паузи).
  - `orders/adapters/clock.py` (ін’єкція часу).
- Оновлено контролери:
  - `orders/views.py` тепер використовує `_get_order_service()`.
  - `current_orders_list` і `order_create` винесені на сервіс.

## Поточний стан
- Бізнес-логіка створення замовлень і зміни статусів ізольована від HTTP-шару.
- Telegram-повідомлення інкапсульовані в адаптері.
- `views.py` зменшився і став thin-controller.

## Відкриті пункти для наступного етапу
- Винести `send_delayed_notifications` у прикладний сервіс або management command.
- Запровадити явну доменну модель для статусів і переходів.
- Додати інтеграційні тести на `OrderService`.
