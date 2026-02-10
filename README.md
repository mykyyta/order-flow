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
Core app: `production`

- `production/domain`: domain rules (statuses, transitions, policies)
- `production/services.py`: orchestration for production lifecycle
- `production/views/`: HTTP layer
- `production/notifications.py`: Telegram notifications

Status model:
- `ProductionOrder.status` is the source of truth for the current state.
- `ProductionOrderStatusHistory` is the audit trail.

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
- **Data model V2**:
  - [v2_model_design_proposal.md](docs/v2_model_design_proposal.md) — цільова структура апок,
    моделі, принципи orchestration, multi-warehouse і план імпорту з legacy.
- **DevOps / Infra** — [docs/devops/](docs/devops/):
  - [Infrastructure overview](docs/devops/infrastructure_overview.md)
  - [Runbook](docs/devops/runbook.md)
  - [Terraform brownfield adoption](docs/devops/terraform_brownfield_migration.md)

## Quick Start (Docker)
```bash
cp .env.example .env
make dev-bootstrap
```

`make dev-bootstrap` does:
- removes old compose containers (`down --remove-orphans`)
- starts db/web in detached mode
- runs migrations
- bootstraps local admin + catalog + sample production orders

If containers are already running:
```bash
make init-local
```

Useful local shortcuts:
```bash
make help            # all commands with descriptions
make dev-refresh     # full backend refresh (same as dev-bootstrap)
make dev-refresh-ui  # full refresh + Tailwind CSS rebuild
make down-reset      # full reset with DB volume removal
```

Manual equivalents:
```bash
docker compose up -d --build
docker compose run --rm web python src/manage.py migrate --run-syncdb
docker compose run --rm web python src/manage.py bootstrap_local --orders 10
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
python src/manage.py migrate
python src/manage.py bootstrap_local --orders 10
python src/manage.py runserver
```

Default local login created by `bootstrap_local`:
- username: `local_admin`
- password: `local-pass-12345`

## Quality Checks
```bash
make test
make check
make lint
```

## Useful Commands
Data consistency check:
```bash
python src/manage.py check_order_statuses
```

Application healthcheck (DB + required tokens):
```bash
python src/manage.py healthcheck_app --require-telegram-token --require-delayed-token
```

Send delayed notifications manually:
```bash
python src/manage.py send_delayed_notifications
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
