# Terraform Brownfield Migration (GCP prod)

## Ціль
Перевести існуючі продові ресурси під Terraform без recreation та без простою.

## Поточний inventory (що вже підтверджено)
- Project: `orderflow-451220`
- Cloud Run service: `orderflow-app` (`us-central1`)
- Service URL: `https://orderflow-app-u5yoasqueq-uc.a.run.app`
- Artifact Registry repo: `my-repo` (`us-central1`, Docker)
- Cloud Run invoker IAM: `allUsers` (`roles/run.invoker`)
- Service account: `841559594474-compute@developer.gserviceaccount.com`
- Додатковий SA: `orderflow-451220@appspot.gserviceaccount.com`

## Критичне зауваження безпеки
Поточний Cloud Run конфіг має plaintext env змінні з чутливими значеннями (бот-токен/DB creds/secret key).  
Після стабілізації Terraform імпорту потрібно виконати ротацію секретів і перейти на Secret Manager.

## Послідовність міграції (safe)
1. Підготувати backend і tfvars:
```bash
cd /Users/myk/Projects/OrderFlow/infra/environments/prod
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

2. Ініціалізувати Terraform:
```bash
terraform init -backend-config=backend.hcl
```

3. Імпортувати існуючі ресурси:
```bash
terraform import -var-file=terraform.tfvars \
  google_artifact_registry_repository.docker \
  projects/orderflow-451220/locations/us-central1/repositories/my-repo

terraform import -var-file=terraform.tfvars \
  google_cloud_run_service.app \
  locations/us-central1/namespaces/orderflow-451220/services/orderflow-app

terraform import -var-file=terraform.tfvars \
  google_cloud_run_service_iam_member.public_invoker \
  v1/projects/orderflow-451220/locations/us-central1/services/orderflow-app roles/run.invoker allUsers
```

4. Зробити перший план:
```bash
terraform plan -var-file=terraform.tfvars
```

5. Очікування для першого плану:
- без destroy
- без recreation сервісу
- мінімальні або нульові зміни

## Швидкий варіант (скрипт)
```bash
cd /Users/myk/Projects/OrderFlow/infra/environments/prod
./import_existing.sh
```

Скрипт використовує короткоживучий токен з `gcloud auth print-access-token` для backend init,
а також для auth Terraform `google` provider, тому окремий `gcloud auth application-default login`
для цього кроку не обов'язковий.

## Статус виконання (2026-02-07)
- Імпорт `google_artifact_registry_repository.docker` виконано.
- Імпорт `google_cloud_run_service.app` виконано.
- Імпорт `google_cloud_run_service_iam_member.public_invoker` виконано.
- Post-import `terraform plan` показав `No changes`.
- Увімкнено `secretmanager.googleapis.com`.
- Створено і взято під Terraform керування:
  - `orderflow-django-secret-key`
  - `orderflow-database-url`
  - `orderflow-telegram-bot-token`
- Додано IAM доступ runtime SA до цих секретів (`roles/secretmanager.secretAccessor`).
- Створено `secret versions` (`v1`) для:
  - `orderflow-django-secret-key`
  - `orderflow-database-url`
  - `orderflow-telegram-bot-token`
- `orderflow-migrate` job повторно імпортовано в Terraform state.
- Job переведено в adoption-режим (`ignore_changes = all`, `prevent_destroy = true`).
- Створено WIF для GitHub Actions:
  - pool: `github-actions-pool`
  - provider: `github-actions-provider`
  - deployer SA: `orderflow-tf-deployer@orderflow-451220.iam.gserviceaccount.com`
- Призначено IAM ролі deployer SA для `run`, `artifact registry`, `secret manager`, `wif`, state bucket.
- Після синхронізації state поточний `terraform plan` знову `No changes`.

## Що далі
1. Прогнати test-run workflow (`workflow_dispatch`) і перевірити:
   - `terraform init/plan/apply` в Actions
   - build/push образу
   - запуск `orderflow-migrate` job після apply.
2. В окремому безпечному кроці перевести Cloud Run service з plaintext env на Secret Manager references + ротація секретів.

Оновлення: GitHub repository variables для `mykyyta/order-flow` вже створені.

## Що поки не імпортуємо
- Domain mapping: не чіпати в першій хвилі, щоб не ризикувати DNS-маршрутом.

## Якщо план показує небезпечні зміни
1. Не запускати `apply`.
2. Зберегти план у файл:
```bash
terraform plan -var-file=terraform.tfvars -out=tfplan
```
3. Перевірити, чи зміни стосуються:
- `google_cloud_run_service.app`
- `google_cloud_run_service_iam_member.public_invoker`
- `google_artifact_registry_repository.docker`
4. Вирівняти Terraform-конфіг під фактичний прод перед повторним запуском.
