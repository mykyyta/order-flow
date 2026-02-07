# Рефакторинг: підсумок та варіанти наступних кроків (2026-02-07)

## Що вже зроблено
- Впроваджено DDD/hex-скелет:
  - домен: `orders/domain/`
  - прикладний шар: `orders/application/`
  - адаптери: `orders/adapters/`
- Винесено бізнес‑логіку зі `views.py` у `OrderService` та `DelayedNotificationService`.
- Додано порти: `OrderRepository`, `NotificationSender`, `Clock`.
- Додано доменні статуси + правила переходів.
- Введено `Order.current_status` як основне джерело правди.
- Міграції:
  - `0005_order_current_status`
  - `0006_alter_orderstatushistory_new_status_and_more` (індекс історії)
- Оптимізовано списки замовлень під `current_status`.
- Додано логування для Telegram‑нотифікацій + таймаут API.
- Оновлено `telegram_bot.py` (Django setup + актуальні поля).
- Додано management commands:
  - `send_delayed_notifications`
  - `check_order_statuses`
- Додані тести (unit + інтеграційні) для сервісів.

## Поточний стан
- Тести проходять.
- Міграції застосовані (неон).
- `current_status` консистентний з історією (перевірка 0 mismatch).

## Варіанти руху далі
### ВАРІАНТ A — Зміцнення ядра (рекомендовано)
1. Закріпити `current_status` як єдине джерело правди (спростити `get_status`).
2. Додати обмеження переходів у UI (disable неприпустимих опцій).
3. Додати healthcheck‑команду (БД + Telegram‑token).

### ВАРІАНТ B — Продуктивність і масштаб
1. Додати `Order.current_status_updated_at` (якщо потрібні SLA/аналітика).
2. Оптимізувати агрегації/пагінацію (select_related + annotations).
3. Додати базове логування подій статусу в окрему таблицю.

### ВАРІАНТ C — Інфраструктура та надійність
1. Перенести нотифікації у фон (Celery/APS) або scheduler в контейнері.
2. Додати retry/дедуплікацію нотифікацій.
3. Підготувати healthcheck endpoint для Cloud Run.

## Рекомендація
Почати з ВАРІАНТУ A, оскільки він закриває функціональну цілісність і стабільність ядра, не змінюючи інфраструктуру.
