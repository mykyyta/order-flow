# Runbook

## Deploy
1. Merge PR into `main`.
2. Check GitHub Actions:
```bash
gh run list --repo mykyyta/order-flow --workflow deploy.yml --branch main --limit 3
gh run list --repo mykyyta/order-flow --workflow terraform-infra.yml --branch main --limit 3
gh run view <RUN_ID> --repo mykyyta/order-flow --log-failed
```

## Fast deploy (default)
On push to `main`, `deploy.yml` updates the Cloud Run service image and **does not run migrations**.

Use this only when DB schema is unchanged. If you changed models/migrations, run the full deploy first.

## Full deploy (manual, with migrations)
Run deploy workflow manually (recommended from `main`, but you can pick a branch in the UI):
```bash
gh workflow run deploy.yml \
  --repo mykyyta/order-flow \
  --ref main \
  -f sync_migrate_job_image=true \
  -f run_migrations=true
```

## PR: skip lint (optional)
If you need to merge quickly and don't want the PR blocked by Ruff, add label `skip-lint` to the PR.

## Manual migrate
```bash
gcloud run jobs execute pult-migrate \
  --region us-central1 \
  --project orderflow-451220 \
  --wait
```

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

## Terraform state recovery
```bash
cd /Users/myk/Projects/OrderFlow/infra/environments/prod
TOKEN="$(gcloud auth print-access-token)"
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=${TOKEN}"
TF_VAR_google_access_token="$TOKEN" terraform state pull > /tmp/pult-prod-state.json
```
Restore previous version from GCS if needed, then run `terraform plan` to confirm consistency.
