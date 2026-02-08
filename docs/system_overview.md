# System Overview

Order management system for small production brand.

## Stack

- Python 3.12, Django 5, PostgreSQL
- Django templates + Tailwind CSS
- Cloud Run (GCP), Terraform

## Structure

```
src/
  config/settings/        # Django settings (base, local, prod, test)
  apps/
    orders/               # Core: orders, status flow, notifications
    catalog/              # Reference data: ProductModel, Color
    accounts/             # Auth, profile, NotificationSetting
frontend/
  templates/              # Django templates
  static/                 # CSS, JS
  assets/                 # Tailwind sources
infra/                    # Terraform (Cloud Run, secrets, WIF)
```

## Data Model

```
CustomUser (AUTH_USER_MODEL)
  └─► NotificationSetting (1:1)
  └─► Order (via history)
  └─► DelayedNotificationLog

Order
  ├─► ProductModel (FK)
  ├─► Color (FK)
  ├─► current_status
  └─► OrderStatusHistory (1:N)
```

## Status Flow

```
new → doing → finished
    → embroidery → finished
    → deciding → ...
    → on_hold → ...
```

Rules in `src/apps/orders/domain/`. Terminal: `finished`. Can't return to `new`.

## Key Files

| Purpose | Location |
|---------|----------|
| Status rules | `src/apps/orders/domain/order_statuses.py` |
| Transitions | `src/apps/orders/domain/transitions.py` |
| Services | `src/apps/orders/services.py` |
| Notifications | `src/apps/orders/notifications.py` |
| Settings | `src/config/settings/` |

## Notifications

- Telegram via bot token (`TELEGRAM_BOT_TOKEN`)
- Immediate: order created, order finished
- Delayed: orders created 18:00-08:00, sent at 08:00

## CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `test.yml` | PR | pytest + ruff |
| `deploy.yml` | push main | build → migrate (if needed) → deploy |
| `infra.yml` | changes in infra/ | terraform apply |

Migrations run only when `*/migrations/*` files changed.

## Environment Variables

```
DJANGO_SECRET_KEY        # Required in prod
DJANGO_SETTINGS_MODULE   # config.settings.{local|prod}
DATABASE_URL             # or POSTGRES_* vars
TELEGRAM_BOT_TOKEN       # For notifications
DELAYED_NOTIFICATIONS_TOKEN  # Internal cron auth
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
LOG_LEVEL                # DEBUG|INFO|WARNING|ERROR
```

## Local Dev

```bash
pip install -r requirements-dev.txt
python src/manage.py migrate
python src/manage.py runserver
```

## Tests

```bash
pytest                   # all tests
pytest src/apps/orders/  # specific app
```
