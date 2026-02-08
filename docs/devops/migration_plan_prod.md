# План міграції прод (OrderFlow → Pult, вже розгорнуто)

У проді вже працюють ресурси з іменами **orderflow-***. У репозиторії зараз закладені імена **pult-***. Якщо просто змержити й запустити Terraform / Deploy, вийде один із сценаріїв:

- **Terraform** з префіксом стану `pult/prod` підніме **порожній** state → плануватиме створення всіх ресурсів з нуля (дублікати в GCP або конфлікти).
- **Deploy** workflow оновлює сервіс `pult-app` і job `pult-migrate` → таких ресурсів у GCP ще немає, деплой впаде.

Нижче — два варіанти: спочатку безпечно викати новий код (Phase 1), потім за бажанням перейти на імена pult-* (Phase 2).

---

## Поточний стан прод (припущення)

| Ресурс | Ім'я в GCP |
|--------|-------------|
| Cloud Run service | `orderflow-app` |
| Cloud Run job (migrate) | `orderflow-migrate` |
| Secret: Django secret | `orderflow-django-secret-key` |
| Secret: DB URL | `orderflow-database-url` |
| Secret: Telegram | `orderflow-telegram-bot-token` |
| Terraform state | bucket = `orderflow-451220-tfstate`, prefix = `orderflow/prod` |

У репозиторії зараз: `pult-app`, `pult-migrate`, `pult-*` секрети, `TF_STATE_PREFIX: pult/prod`.

---

## Phase 1 (рекомендовано): викат нового коду без зміни імен в GCP

Мета: прод продовжує працювати на тих самих ресурсах, але з новим образом (config, Pult у UI).

### 1.1 Повернути в коді імена під існуючий прод

Щоб Terraform і Deploy не намагалися створювати/оновлювати неіснуючі ресурси:

1. **Terraform**
   - `infra/environments/prod/variables.tf`: `service_name` default = `orderflow-app`, `migrate_job_name` = `orderflow-migrate`.
   - `infra/environments/prod/main.tf`: у `locals.secrets` повернути `secret_id`: `orderflow-django-secret-key`, `orderflow-database-url`, `orderflow-telegram-bot-token`; `name_prefix` = `orderflow-${var.environment}`; `app` = `orderflow`.
   - `.github/workflows/terraform-infra.yml`: `TF_STATE_PREFIX: orderflow/prod`, `SERVICE_NAME: orderflow-app`, `MIGRATE_JOB_NAME: orderflow-migrate`.

2. **Deploy**
   - `.github/workflows/deploy.yml`: `SERVICE_NAME: orderflow-app`, `MIGRATE_JOB_NAME: orderflow-migrate`.

3. **Makefile** (для локального `make deploy`): `SERVICE_NAME ?= orderflow-app`.

4. **Документація/runbook**: за потреби повернути в прикладах команд імена `orderflow-app` / `orderflow-migrate` для Phase 1.

Після цих змін Terraform продовжує працювати з існуючим state (`orderflow/prod`) і існуючими ресурсами; deploy оновлює існуючий `orderflow-app` і `orderflow-migrate`.

### 1.2 Виконати деплой

1. Змержити зміни (включно з Phase 1) у `main`.
2. Переконатися, що збирається образ з поточним кодом (config, Pult).
3. Запустити **Deploy** workflow (push у `main` або workflow_dispatch). Він оновить сервіс `orderflow-app` новим образом і при потребі job `orderflow-migrate`.
4. Перевірити сайт і міграції (ручний запуск job якщо потрібно).

Підсумок Phase 1: у проді крутиться новий код (Pult), інфраструктура лишається з іменами orderflow-*.

---

## Phase 2 (опційно): перехід на імена pult-*

Мета: сервіс, job і секрети в GCP називаються pult-app, pult-migrate, pult-*; Terraform state — під префіксом `pult/prod`.

Важливо: робити після стабільного Phase 1, у вікно з можливим коротким простоєм або перемиканням трафіку.

### 2.1 Секрети

У Secret Manager створити нові секрети з тими самими значеннями, що в `orderflow-*`.

#### 2.1.1 Через gcloud CLI

Встанови проєкт і регіон (якщо потрібно):

```bash
export PROJECT_ID=orderflow-451220
```

**Створити секрети і скопіювати значення з існуючих orderflow-*:**

```bash
# 1) Django secret key
gcloud secrets create pult-django-secret-key --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
gcloud secrets versions access latest --secret=orderflow-django-secret-key --project="$PROJECT_ID" | \
  gcloud secrets versions add pult-django-secret-key --data-file=- --project="$PROJECT_ID"

# 2) Database URL
gcloud secrets create pult-database-url --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
gcloud secrets versions access latest --secret=orderflow-database-url --project="$PROJECT_ID" | \
  gcloud secrets versions add pult-database-url --data-file=- --project="$PROJECT_ID"

# 3) Telegram bot token
gcloud secrets create pult-telegram-bot-token --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
gcloud secrets versions access latest --secret=orderflow-telegram-bot-token --project="$PROJECT_ID" | \
  gcloud secrets versions add pult-telegram-bot-token --data-file=- --project="$PROJECT_ID"
```

`2>/dev/null || true` потрібні, щоб не падати, якщо секрет вже існує (наприклад, створений Terraform). Якщо створюєш секрети **до** Terraform apply, прибери `|| true` і переконайся, що секрет ще не створений.

**Альтернатива — скрипт з репо:** `./scripts/create_pult_secrets.sh [PROJECT_ID]` (за замовчуванням `orderflow-451220`). Перед запуском: `chmod +x scripts/create_pult_secrets.sh`.

**Перевірити:** у [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=orderflow-451220) мають з’явитися `pult-django-secret-key`, `pult-database-url`, `pult-telegram-bot-token`, кожен з версією.

Якщо ресурси (секрети, Artifact Registry, WIF, service account) **вже існують** у GCP, а state `pult/prod` порожній, Terraform спробує їх створити і поверне 409. Потрібно імпортувати їх у state. З каталогу `infra/environments/prod` після `terraform init` з prefix `pult/prod`:

**Варіант 1 — скрипт:**  
`chmod +x infra/environments/prod/import_existing_pult_state.sh`  
`./infra/environments/prod/import_existing_pult_state.sh [PROJECT_ID]`

**Варіант 2 — вручну:**
```bash
cd infra/environments/prod
PROJECT_ID=orderflow-451220
terraform import 'google_artifact_registry_repository.docker' "projects/${PROJECT_ID}/locations/us-central1/repositories/my-repo"
terraform import 'google_secret_manager_secret.app["django_secret_key"]' "projects/${PROJECT_ID}/secrets/pult-django-secret-key"
terraform import 'google_secret_manager_secret.app["database_url"]' "projects/${PROJECT_ID}/secrets/pult-database-url"
terraform import 'google_secret_manager_secret.app["telegram_bot_token"]' "projects/${PROJECT_ID}/secrets/pult-telegram-bot-token"
terraform import 'google_service_account.terraform_deployer' "projects/${PROJECT_ID}/serviceAccounts/orderflow-tf-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
terraform import 'google_iam_workload_identity_pool.github_actions' "projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions-pool"
terraform import 'google_iam_workload_identity_pool_provider.github_actions' "projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider"
```
Потім `terraform apply`.

### 2.2 Новий Cloud Run service і job

- У Terraform переключити на pult-*:
  - `variables.tf`: `service_name` = `pult-app`, `migrate_job_name` = `pult-migrate`.
  - `main.tf`: `secret_id` для всіх трьох секретів = `pult-*`; `name_prefix` = `pult-${var.environment}`; `app` = `pult`.
- **State:** щоб не змішувати старі й нові ресурси в одному state:
  - Або перейти на новий префікс state: у workflow Terraform встановити `TF_STATE_PREFIX: pult/prod`, тоді `terraform init -reconfigure` з новим prefix створить новий state і Terraform запланує створення `pult-app`, `pult-migrate`, секретів `pult-*`. Старі ресурси (orderflow-app тощо) залишаться в GCP, але не в новому state — їх потім можна видалити вручну або окремим state.
  - Або залишити state `orderflow/prod` і в Terraform: видалити з конфігу старий сервіс/job (перейменувати ресурси на pult-app/pult-migrate), зробити `terraform state rm` для старих ресурсів, потім `terraform import` для нових після ручного створення — це складніше, тому простіший варіант — новий prefix.

Рекомендовано: новий prefix `pult/prod`.

### 2.3 Порядок дій для Phase 2

1. Створити в GCP секрети `pult-*` (значення = з orderflow-*).
2. У репі: перемкнути Terraform на pult-* (service_name, migrate_job_name, secret_id, name_prefix, app) і `TF_STATE_PREFIX: pult/prod`.
3. Запустити Terraform apply (з новим prefix): створяться `pult-app`, `pult-migrate`, прив’язки до секретів `pult-*`. Старий сервіс/job не чіпати на цьому етапі.
4. У Deploy workflow встановити `SERVICE_NAME: pult-app`, `MIGRATE_JOB_NAME: pult-migrate`.
5. Зібрати образ і задеплоїти його на **pult-app** (один раз deploy у новий сервіс).
6. Запустити job **pult-migrate** (міграції БД).
7. Перемкнути трафік на pult-app:
   - Якщо один URL (за доменом/балансером): оновити backend/URL на новий URL pult-app.
   - Якщо користувачі ходять напряму на Cloud Run URL orderflow-app — можна зробити redirect з orderflow-app на pult-app або змінити посилання/оголошення на новий URL.
8. Після перевірки: видалити (або вимкнути) старий сервіс `orderflow-app` і job `orderflow-migrate` у GCP. Старі секрети orderflow-* можна залишити або видалити пізніше.
9. Makefile / runbook оновити на pult-app / pult-migrate.

Підсумок Phase 2: прод повністю на pult-app, pult-migrate, pult-* секретах; state в `pult/prod`.

---

## Чеклист

**Phase 1 (безпечний викат коду)**  
- [x] Повернути в репо orderflow-app, orderflow-migrate, orderflow-* секрети, TF_STATE_PREFIX orderflow/prod.  
- [ ] Змержити й задеплоїти; перевірити роботу сайту та міграцій.

**Phase 2 (код перемкнено на pult-*)**  
- [ ] Створити секрети pult-* в GCP (скопіювати значення з orderflow-*).  
- [ ] Terraform init з prefix pult/prod, потім apply (створяться pult-app, pult-migrate).
- [ ] Задеплоїти образ на pult-app (Deploy workflow), запустити job pult-migrate.
- [ ] Перемкнути трафік/URL на pult-app.  
- [ ] Прибрати старі orderflow-app, orderflow-migrate (і за бажанням orderflow-* секрети).

---

Якщо хочеш, можу запропонувати конкретні патчі (diff) для Phase 1 по файлах у репо.
