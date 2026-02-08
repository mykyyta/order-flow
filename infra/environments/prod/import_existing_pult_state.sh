#!/usr/bin/env bash
# Import existing GCP resources into Terraform state (pult/prod).
# Prereq: from repo root, run once:
#   cd infra/environments/prod && terraform init -reconfigure \
#     -backend-config="bucket=orderflow-451220-tfstate" -backend-config="prefix=pult/prod"
#
# Usage: from repo root: ./infra/environments/prod/import_existing_pult_state.sh [PROJECT_ID]
#    or: cd infra/environments/prod && ./import_existing_pult_state.sh [PROJECT_ID]
# Default PROJECT_ID: orderflow-451220

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ID="${1:-orderflow-451220}"
REGION="${REGION:-us-central1}"

echo "Importing existing resources into state (project=$PROJECT_ID)..."
echo "Order: secrets first (so for_each can be evaluated), then registry, SA, WIF."

# 1) Secrets first — google_secret_manager_secret_iam_member.runtime_access depends on .app
#    (|| true so "already in state" does not stop the script)
terraform import 'google_secret_manager_secret.app["django_secret_key"]' "projects/${PROJECT_ID}/secrets/pult-django-secret-key" || true
terraform import 'google_secret_manager_secret.app["database_url"]' "projects/${PROJECT_ID}/secrets/pult-database-url" || true
terraform import 'google_secret_manager_secret.app["telegram_bot_token"]' "projects/${PROJECT_ID}/secrets/pult-telegram-bot-token" || true

# 2) Artifact Registry
terraform import 'google_artifact_registry_repository.docker' "projects/${PROJECT_ID}/locations/${REGION}/repositories/my-repo" || true

# 3) Service account and WIF
terraform import 'google_service_account.terraform_deployer' "projects/${PROJECT_ID}/serviceAccounts/orderflow-tf-deployer@${PROJECT_ID}.iam.gserviceaccount.com" || true
terraform import 'google_iam_workload_identity_pool.github_actions' "projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions-pool" || true
terraform import 'google_iam_workload_identity_pool_provider.github_actions' "projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider" || true

# If pult-app and pult-migrate already exist (e.g. from a previous partial apply), uncomment and run:
# terraform import 'google_cloud_run_service.app' "projects/${PROJECT_ID}/locations/${REGION}/services/pult-app"
# terraform import 'google_cloud_run_v2_job.migrate[0]' "projects/${PROJECT_ID}/locations/${REGION}/jobs/pult-migrate"

echo "Done. Run terraform plan to see remaining changes, then terraform apply."
