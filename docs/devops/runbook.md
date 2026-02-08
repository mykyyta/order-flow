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
No domain is configured by default. To use a custom domain:

1. **Verify domain** in [Google Search Console](https://search.google.com/search-console) (add property for the domain; if using a service account for Terraform, add it as owner).
2. **Set domain only where you run Terraform** (never commit the value if you want it private):
   - **CI**: GitHub → Settings → Secrets and variables → Actions → Variables → add `CUSTOM_DOMAIN` = your domain.
   - **Local**: in `infra/environments/prod/terraform.tfvars` set `custom_domain = "your-domain.com"` (this file is gitignored).
3. Run **Terraform** (push to main with infra changes, or manually run "Terraform Infra" workflow). This creates the domain mapping and sets `ALLOWED_HOSTS` for the app.
4. **DNS**: After apply, get records from GCP Console (Cloud Run → pult-app → Manage custom domains) or `terraform output custom_domain_mapping_records`, and add the CNAME (or A/AAAA) at your DNS provider. Wait for propagation.

To remove the custom domain: set `CUSTOM_DOMAIN` / `custom_domain` to empty and apply again.

## Terraform state recovery
```bash
cd /Users/myk/Projects/OrderFlow/infra/environments/prod
TOKEN="$(gcloud auth print-access-token)"
terraform init -reconfigure -backend-config=backend.hcl -backend-config="access_token=${TOKEN}"
TF_VAR_google_access_token="$TOKEN" terraform state pull > /tmp/pult-prod-state.json
```
Restore previous version from GCS if needed, then run `terraform plan` to confirm consistency.
