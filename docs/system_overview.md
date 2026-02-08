# System Overview

## Purpose
Pult is a Django application for managing production orders, tracking status changes, and sending Telegram notifications to users.

## Core modules
- `orders/models.py`: users, orders, colors, product models, status history, notification settings.
- `orders/views.py`: web flows for order lifecycle, auth/profile pages, and internal notification trigger endpoint.
- `orders/application/*`: business services (`OrderService`, delayed notifications).
- `orders/adapters/*`: integrations for clock, notifications, and repository behavior.

## Key flows
- Create order -> save order + status history -> optional Telegram notification.
- Bulk status update -> transition validation -> status/history update.
- Delayed notifications -> scheduled/manual trigger -> send pending messages.

## Runtime configuration
- `config/settings/local.py`: local development defaults.
- `config/settings/prod.py`: production-safe settings.
- Secrets and environment variables control DB, app secret key, Telegram token.

## Data stores
- PostgreSQL for local/dev/prod runtime data.
- SQLite is used for fast test runs.
