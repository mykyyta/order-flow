#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is not installed." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Error: gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

REPO="${1:-mykyyta/pult}"

set_var() {
  local name="$1"
  local value="$2"
  gh variable set "$name" --repo "$REPO" --body "$value"
  echo "Set $name"
}

set_var "GCP_PROJECT_ID" "orderflow-451220"
set_var "GCP_REGION" "us-central1"
set_var "TF_STATE_BUCKET" "orderflow-451220-tfstate"
set_var "ARTIFACT_REPOSITORY" "my-repo"
set_var "GCP_WORKLOAD_IDENTITY_PROVIDER" "projects/841559594474/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider"
set_var "GCP_DEPLOYER_SERVICE_ACCOUNT" "orderflow-tf-deployer@orderflow-451220.iam.gserviceaccount.com"

echo "Done. Repository variables configured for $REPO"
