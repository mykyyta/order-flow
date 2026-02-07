# Тестове середовище

## Передумови
- Python 3.12+
- Віртуальне середовище (рекомендовано)

## Локальний запуск тестів
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py test orders
```

## Примітки
- Під час запуску тестів використовується SQLite (`test_db.sqlite3`), тож PostgreSQL не потрібен.
- Для тестів `SECRET_KEY` автоматично підставляється, якщо `DJANGO_SECRET_KEY` не заданий.
