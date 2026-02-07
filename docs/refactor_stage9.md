# Refactor Stage 9

## Completed
- Locked `Order.get_status()` to `current_status` only.
- Added transition helper `get_allowed_transitions()` in domain layer.
- Added UI transition filtering in current orders page for multi-select updates.
- Added `healthcheck_app` management command with DB and env checks.
- Added tests for model status source, transition map rendering, and healthcheck flags.

## Validation
```bash
python manage.py test orders
```

## Operations
```bash
python manage.py healthcheck_app --require-telegram-token --require-delayed-token
```
