# Pult

Pult is an order management system for small production workflows with Telegram notifications.

## What It Does
- Creates and tracks orders through a fixed status flow.
- Stores full status history for audit.
- Supports bulk status updates.
- Separates active vs finished orders.
- Sends Telegram notifications for order created and finished events.
- Supports delayed notifications for after-hours orders.

## Architecture
Core app: `orders`

- `orders/domain`: domain rules (statuses, transitions, policies)
- `orders/application`: use-cases and ports
- `orders/adapters`: ORM, notifications, and clock adapters
- `orders/views.py`: HTTP layer

Status model:
- `Order.current_status` is the source of truth for the current state.
- `OrderStatusHistory` is the audit trail.

## Tech Stack
- Python 3.12+
- Django 5.1
- PostgreSQL
- SQLite for tests
- Telegram Bot API
- Docker + Docker Compose

## Docs
- **Дизайн і layout** — [docs/design/](docs/design/):
  - **[design_components.md](docs/design/design_components.md)** — єдиний довідник з UI: компоненти, відступи/тіні, чеклісти, куди дивитись при зміні.
  - [style_decisions.md](docs/design/style_decisions.md) — конвенції коду (неймінг, views, шаблони, CSS/JS, мова).
- **DevOps / Infra** — [docs/devops/](docs/devops/):
  - [Infrastructure overview](docs/devops/infrastructure_overview.md)
  - [Runbook](docs/devops/runbook.md)
  - [Terraform brownfield adoption](docs/devops/terraform_brownfield_migration.md)

## Quick Start (Docker)
```bash
cp .env.example .env
docker compose up --build
```

Run migrations in a separate terminal:
```bash
docker compose run --rm web python manage.py migrate
```

Open:
- `http://localhost:8000`

## UI Theme Preview / Palette Lab
Theme preview is controlled via URL param `?theme=<name>` (for quick checks).

Available preview themes:
- `lumen_subtle`
- `lumen_warm`
- `lumen_night`
- `dune_lite`

Palette lab page (requires login):
- `http://localhost:8000/palette/`

## Quick Start (Local Python)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

## Quality Checks
```bash
make test
make check
make lint
```

## Useful Commands
Data consistency check:
```bash
python manage.py check_order_statuses
```

Application healthcheck (DB + required tokens):
```bash
python manage.py healthcheck_app --require-telegram-token --require-delayed-token
```

Send delayed notifications manually:
```bash
python manage.py send_delayed_notifications
```

## Environment Variables
Main variables used by the app:
- `DJANGO_SETTINGS_MODULE`
- `DJANGO_SECRET_KEY`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `DELAYED_NOTIFICATIONS_TOKEN`

See `.env.example` for local defaults.

## Deployment
Single-container deployment to Google Cloud Run.

Build and deploy helpers:
```bash
make build
make push
make deploy
```
