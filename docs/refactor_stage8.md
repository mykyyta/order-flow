# Рефакторинг: Етап 8 (2026-02-07)

## Ціль етапу
Закріпити `current_status` як джерело правди, додати правила переходів і оптимізувати читання історії.

## План етапу
1. Додати контроль дозволених переходів у сервіс.
2. Обробити помилки переходів у UI.
3. Додати індекси для історії статусів.

## Реалізація (виконано)
- Додано `InvalidStatusTransition`:
  - `orders/application/exceptions.py`.
- Перевірка переходів у `OrderService` + обробка у `views.py`:
  - `orders/application/order_service.py`, `orders/views.py`.
- Індекс на історію статусів:
  - `orders/models.py`, міграція `orders/migrations/0006_alter_orderstatushistory_new_status_and_more.py`.

## Міграція
```
python manage.py migrate
```

## Примітки
- `current_status` є основним джерелом правди; історія залишається аудитом.
- У UI при недозволеному переході показується повідомлення.
