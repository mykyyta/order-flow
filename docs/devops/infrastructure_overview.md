# Infrastructure Overview

## Production platform
- Runtime: Google Cloud Run (service `pult-app`, region `us-central1`).
- Container registry: Artifact Registry (`my-repo`).
- Database: Neon PostgreSQL (pooled connection string).
- Secrets: Google Secret Manager.

## Infrastructure as code
- Terraform source: `infra/environments/prod`.
- Remote state: GCS bucket `orderflow-451220-tfstate`.
- Existing GCP resources are imported into Terraform state (brownfield approach).

## CI/CD
- GitHub Actions workflows in `.github/workflows`.
- PR: app lint/tests (`ci.yml`) + Terraform plan (`terraform-infra.yml`).
- Main branch:
  - App changes: build image -> deploy Cloud Run service (`deploy.yml`) (fast path; migrations are manual).
  - Infra changes: Terraform apply (`terraform-infra.yml`).
- Manual full deploy (with migrations) via `workflow_dispatch` inputs in `deploy.yml`.
- Auth between GitHub and GCP: Workload Identity Federation (no static JSON keys).

## Operational model
- Cloud Run scales to zero for low traffic periods.
- Migrations run through dedicated Cloud Run Job (`pult-migrate`). See [migration_orderflow_to_pult.md](../migration_orderflow_to_pult.md).
- Current technical debt: move Cloud Run runtime secrets from plaintext env to Secret Manager references end-to-end.
