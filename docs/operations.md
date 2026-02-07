# Операційні команди

## Перевірка консистентності статусів
Перевіряє, чи співпадає `Order.current_status` з останнім записом історії.

```
python manage.py check_order_statuses
```

Щоб автоматично виправити:
```
python manage.py check_order_statuses --fix
```

Для вибірки (sampling):
```
python manage.py check_order_statuses --limit 100
```
