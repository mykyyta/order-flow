# Terraform Infrastructure

Terraform is the source of truth for GCP infrastructure in this repository.

## Layout

- `environments/prod`: root module for production stack
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
- CI will use the same root module in `environments/prod`.
- Brownfield adoption guide: `docs/devops/terraform_brownfield_migration.md`.
