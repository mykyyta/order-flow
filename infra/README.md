# Terraform Infrastructure

Terraform is the source of truth for GCP infrastructure in this repository.

## Layout

- `environments/prod`: root module for production stack
- `environments/staging`: root module for staging stack
- `modules/*`: reusable modules for Cloud Run, Secrets, IAM, WIF, Artifact Registry

## Quick start (prod)

1. Create a remote state bucket (once):
   - `gsutil mb -l us-central1 gs://<your-terraform-state-bucket>`
   - `gsutil versioning set on gs://<your-terraform-state-bucket>`
2. Prepare config:
   - `cp environments/prod/backend.hcl.example environments/prod/backend.hcl`
   - `cp environments/prod/terraform.tfvars.example environments/prod/terraform.tfvars`
3. Initialize and plan:
   - `cd environments/prod`
   - `terraform init -backend-config=backend.hcl`
   - `terraform plan -var-file=terraform.tfvars`

## Notes

- `backend.hcl` and `terraform.tfvars` should stay out of git history.
- **State path:** CI uses bucket from `TF_STATE_BUCKET` and prefix `pult/prod`. Your local `backend.hcl` must use the same (`prefix = "pult/prod"`) so pipeline and local share one state. See runbook “Terraform state: one path for pipeline and local”.
- CI will use the same root module in `environments/prod`.
- Brownfield adoption guide: `docs/devops/terraform_brownfield_migration.md`.

## Quick start (staging)

1. Prepare config:
   - `cp environments/staging/backend.hcl.example environments/staging/backend.hcl`
   - `cp environments/staging/terraform.tfvars.example environments/staging/terraform.tfvars`
2. Initialize and plan:
   - `cd environments/staging`
   - `terraform init -backend-config=backend.hcl`
   - `terraform plan -var-file=terraform.tfvars`

Notes:
- Use a different state prefix than prod (default: `pult/staging`).
- Use a different secret prefix than prod (default: `pult-staging`).
- Keep `manage_shared_ci_resources = false` for staging (prod state remains owner of shared CI/WIF/Artifact Registry resources).
- If Telegram notifications are not needed on staging, set `enable_telegram_bot_token_secret = false`.
