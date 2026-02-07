# Runbook: Prod (Terraform + Cloud Run)

## Scope
Операційні дії для `orderflow-451220` (`us-central1`) після переходу на Terraform.

## Передумови
- Доступ до GitHub repo: `mykyyta/order-flow`
- `gcloud` авторизований і проект активний:
  - `gcloud auth login`
  - `gcloud config set project orderflow-451220`
- `terraform` встановлений (локально, для аварійних дій)

## Deploy (штатний шлях)
1. Відкрити PR у `main`.
2. Переконатися, що `CI` + `Terraform Infra` (plan) зелені.
3. Merge PR у `main`.
4. Перевірити `Terraform Infra` (apply) на `main`:
```bash
gh run list --repo mykyyta/order-flow --workflow terraform-infra.yml --branch main --limit 3
gh run view <RUN_ID> --repo mykyyta/order-flow --log-failed
```
5. Переконатися, що `Run migrations job` завершився успішно.

## Migrate (ручний запуск)
```bash
gcloud run jobs execute orderflow-migrate \
  --region us-central1 \
  --project orderflow-451220 \
  --wait
```

Перевірка останніх виконань:
```bash
gcloud run jobs executions list \
  --job orderflow-migrate \
  --region us-central1 \
  --project orderflow-451220 \
  --limit 5
```

## Health-check (prod)
1. Отримати URL сервісу:
```bash
SERVICE_URL="$(gcloud run services describe orderflow-app \
  --region us-central1 \
  --project orderflow-451220 \
  --format='value(status.url)')"
echo "$SERVICE_URL"
```
2. Базова HTTP перевірка:
```bash
curl -fSsL "$SERVICE_URL/" >/dev/null && echo "OK"
```
3. Перевірити останню готову ревізію:
```bash
gcloud run services describe orderflow-app \
  --region us-central1 \
  --project orderflow-451220 \
  --format='value(status.latestReadyRevisionName,status.latestCreatedRevisionName)'
```

## Rollback (сервіс)
1. Подивитися ревізії:
```bash
gcloud run revisions list \
  --service orderflow-app \
  --region us-central1 \
  --project orderflow-451220
```
2. Переключити трафік на попередню стабільну ревізію:
```bash
gcloud run services update-traffic orderflow-app \
  --region us-central1 \
  --project orderflow-451220 \
  --to-revisions <GOOD_REVISION>=100
```
3. Зафіксувати rollback у git (revert проблемного PR) і пройти штатний deploy.

## Terraform state recovery (аварійно)
Перед будь-якими аварійними діями зробити бекап поточного state:
```bash
cd /Users/myk/Projects/OrderFlow/infra/environments/prod
TOKEN="$(gcloud auth print-access-token)"
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=${TOKEN}"
TF_VAR_google_access_token="$TOKEN" terraform state pull > "/tmp/orderflow-prod-state-$(date +%Y%m%d-%H%M%S).json"
```

Відновлення з версіонованого state у GCS:
1. Знайти доступні покоління:
```bash
gcloud storage ls -a "gs://orderflow-451220-tfstate/orderflow/prod/default.tfstate"
```
2. Завантажити потрібну historical-версію:
```bash
gcloud storage cp "gs://orderflow-451220-tfstate/orderflow/prod/default.tfstate#<GENERATION>" /tmp/terraform.tfstate.recovered
```
3. Запушити recovered state:
```bash
TF_VAR_google_access_token="$TOKEN" terraform state push /tmp/terraform.tfstate.recovered
```

Після recovery обов'язково:
```bash
TF_VAR_google_access_token="$TOKEN" terraform plan -var-file=terraform.tfvars
```

## Відомий технічний борг
- Поточний Cloud Run сервіс ще треба перевести з plaintext env на Secret Manager references (окремим безпечним change-set з ротацією секретів).
