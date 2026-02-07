# DevOps стратегія та план впровадження (Terraform-first, станом на 2026-02-07)

## Мета
- Швидке і зручне середовище розробки локально.
- Керовані `local/dev/prod` конфіги без хардкоду.
- Легкий і надійний CI/CD для Django в Cloud Run.
- Базова якість коду (лінтери, автоперевірки) без зайвої складності.
- Вся інфраструктура через Terraform як єдине джерело правди.

## Стратегія
1. Єдина модель конфігурації застосунку: `base/local/prod`, всі критичні значення через env.
2. Паритет середовищ: локальний запуск максимально близький до продового.
3. Security by default: секрети в Secret Manager, без секретів у репозиторії.
4. Fast feedback: мінімальний CI на кожен PR (`lint + tests + django checks`).
5. Terraform-first: Cloud Run, Secret Manager, IAM, WIF, Artifact Registry описані в IaC.
6. Поступове посилення: спочатку стабільний pipeline, потім додаткові перевірки.

## Прийняті рішення
- Локальне dev-середовище використовує окремий локальний PostgreSQL у `docker-compose`.
- Тести залишаються на SQLite (як зараз) для швидкості.
- Продове середовище: Cloud Run + Neon pooled `DATABASE_URL`.
- Міграції: окремий Cloud Run Job (`python manage.py migrate`).
- Інфраструктурні зміни виконуються через Terraform.
- CI/CD цільовий шлях: GitHub Actions + WIF + `terraform plan/apply`.

## Поточний статус (що вже виконано)
- [x] Проведено технічний аналіз поточного стану проєкту.
- [x] Критично оцінено цільову Cloud Run архітектуру.
- [x] Узгоджено підхід до локальної БД (окрема локальна PostgreSQL для dev).
- [x] Розділено Django settings на `base/local/prod`. (2026-02-07)
- [x] Оновлено локальний dev baseline (`docker-compose`, `.env.example`, `makefile`, quickstart в README). (2026-02-07)
- [x] Переведено контейнер на `gunicorn` + WhiteNoise. (2026-02-07)
- [x] Додано `ruff` + `pre-commit` (конфіг + команди). (2026-02-07)
- [x] Додано GitHub Actions для PR (`lint + tests + check`). (2026-02-07)
- [x] Підготовлено GitHub Actions workflow для Terraform-based deploy (`plan/apply`). (2026-02-07)
- [x] Додано Terraform структуру (`infra/`, backend state, environments). (2026-02-07)
- [x] Додано Terraform brownfield baseline для існуючих ресурсів (`Artifact Registry`, `Cloud Run service`, `public invoker IAM`) в adoption-режимі. (2026-02-07)
- [x] Описано в Terraform Cloud Run Job, Secret Manager, IAM, WIF. (2026-02-07)
  Деталі: `secret versions` створені, `orderflow-migrate` імпортовано в state, WIF + deployer SA застосовані.
- [x] Виконано brownfield-міграцію існуючих GCP ресурсів (import в state без recreation) для поточного baseline:
  `Artifact Registry`, `Cloud Run service`, `public invoker IAM`. (2026-02-07)
  Підтвердження: post-import `terraform plan` -> `No changes`.
- [x] Переведено deploy workflow на `terraform plan/apply`. (2026-02-07)
  Примітка: GitHub repository variables вже підв'язані через `gh` (`mykyyta/order-flow`).
- [x] Додано runbook для deploy/rollback/migrate. (2026-02-07)

## Покроковий план

### Етап 1. Конфігурація застосунку (local/dev/prod)
1. Розбити `/Users/myk/Projects/OrderFlow/OrderFlow/settings.py` на `settings/base.py`, `settings/local.py`, `settings/prod.py`.
2. У `base` винести спільне: apps, middleware, templates, timezone, auth model.
3. У `local`:
   - `DEBUG=True`
   - підключення до локального Postgres (`db` у docker-compose)
4. У `prod`:
   - `DEBUG=False`
   - `DATABASE_URL` (Neon pooled)
   - безпечні cookie/CSRF/SSL налаштування
5. Додати перевірки env на старті (помилка при відсутніх критичних значеннях).

Критерій готовності:
- Запуск у `local` і `prod` керується тільки env-перемінними.

### Етап 2. Локальне середовище розробки
1. Оновити `/Users/myk/Projects/OrderFlow/docker-compose.yml`:
   - `web` + `db`
   - окрема dev БД (`orderflow_dev`)
2. Додати `/Users/myk/Projects/OrderFlow/.env.example` з повним переліком env.
3. Оновити `/Users/myk/Projects/OrderFlow/makefile`:
   - `make dev` (up)
   - `make down`
   - `make migrate`
   - `make test`
   - `make lint`
   - `make format`
4. Описати короткий quickstart у README.

Критерій готовності:
- Новий розробник піднімає проєкт локально за 5-10 хвилин.

### Етап 3. Контейнер для prod
1. Оновити `/Users/myk/Projects/OrderFlow/Dockerfile`:
   - запуск через `gunicorn OrderFlow.wsgi:application`
   - додати `gunicorn`, `whitenoise` у залежності
2. Налаштувати статичні файли через WhiteNoise:
   - middleware
   - `STATIC_ROOT`
   - storage backend
3. Додати команду `collectstatic` у процес build/release.

Критерій готовності:
- Контейнер Cloud Run стартує стабільно без `runserver`.

### Етап 4. Якість коду і DX
1. Додати `pyproject.toml` з `ruff` (lint + format).
2. Додати `.pre-commit-config.yaml`:
   - `ruff check`
   - `ruff format`
3. Додати інструкцію підключення pre-commit.

Критерій готовності:
- Локально перед commit автоматично проходять базові перевірки стилю.

### Етап 5. Легкий CI для PR
1. Додати workflow перевірок на PR:
   - install deps
   - `ruff check`
   - `python manage.py check`
   - `python manage.py test orders`
2. Додати pip cache для прискорення.

Критерій готовності:
- PR не може бути змерджений при падінні перевірок.

### Етап 6. Terraform фундамент
1. Створити каталог `/Users/myk/Projects/OrderFlow/infra` з базовою структурою:
   - `infra/environments/prod`
   - `infra/modules/*`
2. Налаштувати backend для state (GCS bucket з versioning + lock через GCS generation).
3. Додати `providers.tf`, `versions.tf`, `variables.tf`, `outputs.tf`.
4. Визначити naming convention для ресурсів.

Критерій готовності:
- `terraform init/plan` для `prod` працює стабільно.

### Етап 7. Terraform ресурси Cloud Run/GCP
1. Описати в Terraform:
   - Artifact Registry repository
   - Cloud Run service
   - Cloud Run job для міграцій
   - Secret Manager secrets + IAM доступ сервісного акаунта
   - Service accounts + IAM roles
2. Додати керовані параметри Cloud Run:
   - `min instances=0`
   - `max instances=1-2`
   - `concurrency=10-20`
3. Передбачити зміну image тегу через змінну `container_image`.

Критерій готовності:
- Повний стек прод-інфраструктури піднімається через `terraform apply`.

### Етап 8. Brownfield-міграція існуючого прода
1. Зафіксувати inventory поточних ресурсів:
   - Cloud Run service + domain mapping
   - Cloud Run job для міграцій
   - Artifact Registry
   - Secret Manager secrets
   - Service accounts + IAM
2. Описати ці ресурси в Terraform без змін критичних параметрів.
3. Імпортувати існуючі ресурси в state (`terraform import`), а не створювати нові.
4. Для критичних ресурсів тимчасово ввімкнути захист:
   - `lifecycle.prevent_destroy = true`
5. Перший `terraform plan` має бути `no-op` або з мінімальними безпечними змінами.
6. Domain mapping не переносити агресивно:
   - якщо вже стабільний у проді, спершу залишити як є і не робити recreation.

Критерій готовності:
- Terraform керує існуючим продом без простою та без змін DNS-маршрутизації.

### Етап 9. CI/CD через Terraform
1. Замінити тимчасовий deploy workflow на:
   - build/push image
   - `terraform plan` (PR)
   - `terraform apply` (main, з manual approval за потреби)
2. Налаштувати OIDC між GitHub Actions і GCP (без static key JSON).
3. Забезпечити запуск Cloud Run Job міграцій після оновлення сервісу.

Критерій готовності:
- Деплой і інфраструктурні зміни проходять тільки через Terraform workflow.

### Етап 10. Операційний runbook
1. Додати короткий runbook у `/Users/myk/Projects/OrderFlow/docs`:
   - deploy
   - migrate
   - rollback
   - перевірка здоров'я сервісу
   - аварійне відновлення state

Критерій готовності:
- Є чітка операційна інструкція для команди.

## Порядок виконання
1. Етап 1
2. Етап 2
3. Етап 3
4. Етап 4
5. Етап 5
6. Етап 6
7. Етап 7
8. Етап 8
9. Етап 9
10. Етап 10

## Примітка до оновлення статусів
- Після завершення кожного етапу оновлювати чекліст у цьому файлі.
- Для прозорості додавати дату завершення поруч із пунктом.
