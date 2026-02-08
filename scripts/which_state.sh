#!/usr/bin/env bash
# Detect which Terraform state path (orderflow/prod vs pult/prod) has the "current" config.
# Run from repo root. Requires: gcloud auth, terraform, cd to infra/environments/prod.
set -euo pipefail

BUCKET="orderflow-451220-tfstate"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROD_DIR="$(cd "$SCRIPT_DIR/../infra/environments/prod" && pwd)"

echo "=== Checking state at gs://${BUCKET}/orderflow/prod/ ==="
if gsutil -q stat "gs://${BUCKET}/orderflow/prod/default.tfstate" 2>/dev/null; then
  echo "  File exists."
else
  echo "  No default.tfstate (or not accessible)."
fi

echo ""
echo "=== Checking state at gs://${BUCKET}/pult/prod/ ==="
if gsutil -q stat "gs://${BUCKET}/pult/prod/default.tfstate" 2>/dev/null; then
  echo "  File exists."
else
  echo "  No default.tfstate (or not accessible)."
fi

echo ""
echo "=== Which state has pult-app? (init with each prefix and show cloud_run_service_name) ==="
cd "$PROD_DIR"
for PREFIX in orderflow/prod pult/prod; do
  echo "--- prefix: $PREFIX ---"
  terraform init -reconfigure -backend-config="bucket=${BUCKET}" -backend-config="prefix=${PREFIX}" -backend-config="access_token=$(gcloud auth print-access-token)" -input=false >/dev/null 2>&1
  OUT=$(terraform output -raw cloud_run_service_name 2>/dev/null || echo "(failed)")
  echo "  cloud_run_service_name = $OUT"
  echo ""
done

echo "Done. The prefix where cloud_run_service_name = pult-app is the state you want to keep."
echo "Set backend.hcl to that prefix (pult/prod) so pipeline and local use the same state."
