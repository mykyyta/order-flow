#!/usr/bin/env bash
# Create pult-* secrets in GCP Secret Manager by copying values from orderflow-*.
# Run after Phase 1 deploy. Requires gcloud and access to the project.
#
# Usage: ./scripts/create_pult_secrets.sh [PROJECT_ID]
# Default PROJECT_ID: orderflow-451220

set -euo pipefail

PROJECT_ID="${1:-orderflow-451220}"

echo "Using project: $PROJECT_ID"

copy_secret() {
  local old_name="$1"
  local new_name="$2"
  echo "Creating $new_name from $old_name..."
  gcloud secrets create "$new_name" --project="$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
  gcloud secrets versions access latest --secret="$old_name" --project="$PROJECT_ID" | \
    gcloud secrets versions add "$new_name" --data-file=- --project="$PROJECT_ID"
}

copy_secret "orderflow-django-secret-key" "pult-django-secret-key"
copy_secret "orderflow-database-url" "pult-database-url"
copy_secret "orderflow-telegram-bot-token" "pult-telegram-bot-token"

echo "Done. Verify at: https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
