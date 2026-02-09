# Runbook

## Deploy
1. Merge PR into `main`.
2. Check GitHub Actions:
```bash
gh run list --repo mykyyta/pult --workflow deploy.yml --branch main --limit 3
gh run list --repo mykyyta/pult --workflow terraform-infra.yml --branch main --limit 3
gh run view <RUN_ID> --repo mykyyta/pult --log-failed
```

## Deploy behaviour
On push to `main`, `deploy.yml` builds the image, **runs migrations** (updates migrate job image and executes it), then updates the Cloud Run service.

**Why Cloud Run could show an old container:** Previously, `infra.yml` (on push to `infra/**`) ran `terraform apply` without passing `container_image`. Terraform then set the service (and migrate job) image back to the default `var.container_image` (no SHA tag), so the live image reverted to an older one. This is fixed: Terraform now has `ignore_changes = [template]` on the Cloud Run service and migrate job, so the image is owned only by `deploy.yml`.

## PR: skip lint (optional)
If you need to merge quickly and don't want the PR blocked by Ruff, add label `skip-lint` to the PR.

## Manual migrate
The migrate job runs whatever **image** it was last updated to. If the app was deployed without running migrations (e.g. fast deploy), the job may still use an old image and will not create new tables. So first point the job at the current app image, then run it:

```bash
REGION=us-central1
PROJECT=orderflow-451220

# Use same image as the running app
IMAGE=$(gcloud run services describe pult-app --region "$REGION" --project "$PROJECT" --format='value(spec.template.spec.containers[0].image)')
gcloud run jobs update pult-migrate --region "$REGION" --project "$PROJECT" --image "$IMAGE"

# Then run migrations
gcloud run jobs execute pult-migrate --region "$REGION" --project "$PROJECT" --wait
```

Check the job run in Cloud Console (Cloud Run → Jobs → pult-migrate → Executions) for logs and exit status.

### Fix "can't open file '/app/manage.py'"
If the job fails with `can't open file '/app/manage.py': No such file or directory`, the job's container command is wrong (it expects `manage.py` in `/app`; the image has it at `src/manage.py`). One-time fix:

```bash
REGION=us-central1
PROJECT=orderflow-451220

gcloud run jobs update pult-migrate --region "$REGION" --project "$PROJECT" \
  --command="python" --args="src/manage.py,migrate,--noinput"
```

Then run the job again: `gcloud run jobs execute pult-migrate --region "$REGION" --project "$PROJECT" --wait`. Alternatively, fix via Terraform: the migrate job no longer has `ignore_changes = all`, so `terraform apply` will update the job's command to `python src/manage.py migrate --noinput`.

## Data consistency check
```bash
python manage.py check_order_statuses
```

## Health check
```bash
python manage.py healthcheck_app --require-telegram-token --require-delayed-token
```

External check:
```bash
SERVICE_URL="$(gcloud run services describe pult-app --region us-central1 --project orderflow-451220 --format='value(status.url)')"
curl -fSsL "$SERVICE_URL/" >/dev/null && echo "OK"
```

## Rollback
1. List revisions:
```bash
gcloud run revisions list --service pult-app --region us-central1 --project orderflow-451220
```
2. Route 100% traffic to a known good revision:
```bash
gcloud run services update-traffic pult-app \
  --region us-central1 \
  --project orderflow-451220 \
  --to-revisions <GOOD_REVISION>=100
```

## Custom domain (optional)
No domain by default. To add one:

1. **Verify domain** in [Search Console](https://search.google.com/search-console) (Domain property for the base domain, e.g. `example.com` for `app.example.com`).
2. **Add Terraform deployer SA as Verified owner:** Search Console → property → Settings → **Verified owners** → Add owner → `orderflow-tf-deployer@orderflow-451220.iam.gserviceaccount.com`. Otherwise apply fails with "Caller is not authorized to administer the domain".
3. **Set domain** (don’t commit): GitHub Actions variable `CUSTOM_DOMAIN` or local `terraform.tfvars`: `custom_domain = "your-domain.com"`.
4. **Terraform apply** (workflow or local). Then add the DNS records shown in Console (Cloud Run → Domain mappings → DNS records) or `gcloud beta run domain-mappings describe --domain=your-domain.com --region us-central1 --project orderflow-451220 --format="yaml(status.resourceRecords)"`.

To remove: set `CUSTOM_DOMAIN` / `custom_domain` to empty and apply again.

## WIF / GitHub Actions auth after repo rename
If the pipeline fails with either:
- **"The given credential is rejected by the attribute condition"** (federated token rejected by WIF provider), or
- **"Permission 'iam.serviceAccounts.getAccessToken' denied"** for the deployer SA,

the WIF provider and IAM binding in GCP are still scoped to the **old** repo (e.g. `mykyyta/order-flow`). They must allow the **new** repo (e.g. `mykyyta/pult`).

**Fix:** run Terraform apply **locally** once so that `github_repository` (in `terraform.tfvars` or env) is the new repo. That updates:
- WIF provider `attribute_condition` to the new repo
- IAM member `principalSet://.../attribute.repository/<new-repo>` with `roles/iam.workloadIdentityUser` on the deployer SA

From repo root:
```bash
cd infra/environments/prod
# Ensure backend and vars use the new repo (e.g. github_repository = "mykyyta/pult")
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=$(gcloud auth print-access-token)"
terraform plan   # expect: WIF provider + SA IAM member changes
# If plan tries to destroy other resources (e.g. Cloud Run with prevent_destroy), apply only WIF:
terraform apply \
  -target=google_iam_workload_identity_pool_provider.github_actions \
  -target=google_service_account_iam_member.github_actions_wif_user
# Or full: terraform apply
```
After that, re-run the failing workflow.

## Terraform state: one path for pipeline and local (avoid drift)
**Cause of “state збився після пайплайну”:** Pipeline and local used **different state paths**. Pipeline uses `bucket=TF_STATE_BUCKET`, `prefix=pult/prod`. If local `backend.hcl` had `prefix=orderflow/prod`, you had two states; pipeline apply then synced GCP to the (old) state in `pult/prod`.

**Rule:** Everyone must use the **same** state: bucket `orderflow-451220-tfstate`, prefix **`pult/prod`**.

- **Pipeline:** Already uses `TF_STATE_BUCKET` (from vars) and `TF_STATE_PREFIX=pult/prod` in the workflow.
- **Local:** In `infra/environments/prod/backend.hcl` (gitignored) set:
  - `bucket = "orderflow-451220-tfstate"`
  - `prefix = "pult/prod"`
  Use `backend.hcl.example` as reference; copy to `backend.hcl` and run `terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=$(gcloud auth print-access-token)"`.

**If the “good” state was only in `orderflow/prod`:** Copy it once into `pult/prod` so the pipeline sees it, then use only `pult/prod`:
```bash
# One-time: backup pult/prod, then copy good state from orderflow/prod to pult/prod
gsutil cp gs://orderflow-451220-tfstate/pult/prod/default.tfstate \
  gs://orderflow-451220-tfstate/pult/prod/default.tfstate.backup  # optional
gsutil cp gs://orderflow-451220-tfstate/orderflow/prod/default.tfstate \
  gs://orderflow-451220-tfstate/pult/prod/default.tfstate
```
Then set local `backend.hcl` to `prefix = "pult/prod"` and run `terraform plan` to confirm.

**If pipeline already overwrote GCP with old state:** Re-import current GCP resources into the state that pipeline uses (`pult/prod`): see “State points to orderflow-app” and “Re-import secrets as pult-*” below. Then fix `backend.hcl` to `pult/prod` so it never drifts again.

## State points to orderflow-app instead of pult-app
If you already migrated to pult (pult-app exists in GCP) but Terraform state or outputs still show `orderflow-app`, state was likely written by an old run (e.g. local tfvars with `service_name = "orderflow-app"` or another state prefix). Fix by re-importing the **existing** pult-app into state (no destroy in GCP).

1. **Use the same state as the pipeline** (bucket + prefix `pult/prod`). In `infra/environments/prod`, ensure `backend.hcl` has `prefix = "pult/prod"`.
2. **Ensure config uses pult-app:** in `terraform.tfvars` set `service_name = "pult-app"` (or rely on default in `variables.tf`). If you had `orderflow-app` there, change it and keep it as `pult-app`.
3. **Re-import Cloud Run service and its IAM binding** (from repo root, or `cd infra/environments/prod`):
```bash
cd infra/environments/prod
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=$(gcloud auth print-access-token)"

# Remove wrong service from state (does not delete anything in GCP)
terraform state rm 'google_cloud_run_service.app'
terraform state rm 'google_cloud_run_service_iam_member.public_invoker'

# Import existing pult-app (must exist in GCP). Use provider's expected format:
terraform import 'google_cloud_run_service.app' 'locations/us-central1/namespaces/orderflow-451220/services/pult-app'
terraform import 'google_cloud_run_service_iam_member.public_invoker' 'v1/projects/orderflow-451220/locations/us-central1/services/pult-app roles/run.invoker allUsers'
terraform plan   # should be clean or only unrelated changes
```
4. If you use the migrate job and it’s in state, re-import it too if needed (see commented lines in `import_existing_pult_state.sh`).

**If plan still wants to change the container** (secrets → orderflow-* or ALLOWED_HOSTS loses domain): Re-import the three secrets as `pult-*` and their IAM members; set `custom_domain = "pult.woolberry.ua"` in terraform.tfvars. See commands in runbook or below.

## Terraform state recovery
From repo root:
```bash
cd infra/environments/prod
TOKEN="$(gcloud auth print-access-token)"
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=${TOKEN}"
TF_VAR_google_access_token="$TOKEN" terraform state pull > /tmp/pult-prod-state.json
```
Restore previous version from GCS if needed, then run `terraform plan` to confirm consistency.

## Re-import secrets as pult-* (when plan switches container to orderflow-*)
From `infra/environments/prod`, after state rm of the three `google_secret_manager_secret.app` and three `runtime_access` IAM members:
```bash
terraform import 'google_secret_manager_secret.app["django_secret_key"]' 'projects/orderflow-451220/secrets/pult-django-secret-key'
terraform import 'google_secret_manager_secret.app["database_url"]' 'projects/orderflow-451220/secrets/pult-database-url'
terraform import 'google_secret_manager_secret.app["telegram_bot_token"]' 'projects/orderflow-451220/secrets/pult-telegram-bot-token'
SA="841559594474-compute@developer.gserviceaccount.com"
terraform import 'google_secret_manager_secret_iam_member.runtime_access["django_secret_key"]' "projects/orderflow-451220/secrets/pult-django-secret-key roles/secretmanager.secretAccessor serviceAccount:${SA}"
terraform import 'google_secret_manager_secret_iam_member.runtime_access["database_url"]' "projects/orderflow-451220/secrets/pult-database-url roles/secretmanager.secretAccessor serviceAccount:${SA}"
terraform import 'google_secret_manager_secret_iam_member.runtime_access["telegram_bot_token"]' "projects/orderflow-451220/secrets/pult-telegram-bot-token roles/secretmanager.secretAccessor serviceAccount:${SA}"
```
Set `custom_domain = "pult.woolberry.ua"` in terraform.tfvars so ALLOWED_HOSTS is not reduced.
