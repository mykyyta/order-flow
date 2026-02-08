# OrderFlow → Pult

## Поточний стан

- **Бренд у коді:** `config/settings/base.py` — `SITE_NAME`, `SITE_WORDMARK`, `SITE_EMOJI`; context processor передає їх у шаблони як `site_name`, `site_wordmark`, `site_emoji`.
- **Django-пакет:** `config/` (було `OrderFlow/`).

## Інфраструктура (ідентифікатори)

| Що | Значення |
|----|----------|
| GCP project | `orderflow-451220` |
| Cloud Run service | `pult-app` |
| Cloud Run job (migrate) | `pult-migrate` |
| Секрети | `pult-django-secret-key`, `pult-database-url`, `pult-telegram-bot-token` |
| Terraform state | bucket `orderflow-451220-tfstate`, prefix `pult/prod` |

Оперативні кроки — у [docs/devops/runbook.md](devops/runbook.md).
