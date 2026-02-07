# Infrastructure Overview

## Production platform
- Runtime: Google Cloud Run (`orderflow-app`, region `us-central1`).
- Container registry: Artifact Registry (`my-repo`).
- Database: Neon PostgreSQL (pooled connection string).
- Secrets: Google Secret Manager.

## Infrastructure as code
- Terraform source: `infra/environments/prod`.
- Remote state: GCS bucket `orderflow-451220-tfstate`.
- Existing GCP resources are imported into Terraform state (brownfield approach).

## CI/CD
- GitHub Actions workflows in `.github/workflows`.
- PR: lint/tests + Terraform plan.
- Main branch: build image -> Terraform apply -> run Cloud Run migrate job.
- Auth between GitHub and GCP: Workload Identity Federation (no static JSON keys).

## Operational model
- Cloud Run scales to zero for low traffic periods.
- Migrations run through dedicated Cloud Run Job (`orderflow-migrate`).
- Current technical debt: move Cloud Run runtime secrets from plaintext env to Secret Manager references end-to-end.
