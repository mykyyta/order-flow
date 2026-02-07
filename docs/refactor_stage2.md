# Рефакторинг: Етап 2 (2026-02-07)

## Ціль етапу
Перемістити відкладені нотифікації в прикладний сервіс та додати базові тести для прикладного шару.

## План етапу
1. Створити `DelayedNotificationService`.
2. Розширити порти `OrderRepository` і `NotificationSender`.
3. Додати Django‑адаптери для вибірки замовлень і відкладених нотифікацій.
4. Перепідключити `send_delayed_notifications` на новий сервіс.
5. Додати базові юніт‑тести для `OrderService` та `DelayedNotificationService`.

## Реалізація (виконано)
- Додано `orders/application/notification_service.py`.
- Розширено порти:
  - `orders/application/ports.py`.
- Розширено адаптери:
  - `orders/adapters/orders_repository.py` (діапазон дат).
  - `orders/adapters/notifications.py` (відкладені нотифікації).
- `send_delayed_notifications` переведено на сервіс у `orders/views.py`.
- Додані тести у `orders/tests.py` (SimpleTestCase, без БД).

## Поточний стан
- Відкладені нотифікації більше не залежать від HTTP‑логіки.
- Є тестова опора для сервісів.

## Наступні кроки
- Винести правила статусів у доменний шар (перехідні правила).
- Додати інтеграційні тести з Django ORM.
- Розглянути `Order.current_status` для оптимізації.
