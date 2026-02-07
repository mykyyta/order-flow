#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is not installed or not in PATH"
  exit 1
fi

if [[ ! -f backend.hcl ]]; then
  echo "Missing backend.hcl. Create it from backend.hcl.example first."
  exit 1
fi

if [[ ! -f terraform.tfvars ]]; then
  echo "Missing terraform.tfvars. Create it from terraform.tfvars.example first."
  exit 1
fi

PROJECT_ID="${PROJECT_ID:-orderflow-451220}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-orderflow-app}"
REPOSITORY_ID="${REPOSITORY_ID:-my-repo}"

echo "== terraform init =="
BACKEND_ARGS=(-reconfigure -backend-config=backend.hcl)
if command -v gcloud >/dev/null 2>&1; then
  ACCESS_TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
  if [[ -n "${ACCESS_TOKEN}" ]]; then
    BACKEND_ARGS+=("-backend-config=access_token=${ACCESS_TOKEN}")
    export TF_VAR_google_access_token="${ACCESS_TOKEN}"
  fi
fi
terraform init "${BACKEND_ARGS[@]}"

echo "== terraform import: Artifact Registry =="
terraform import -var-file=terraform.tfvars \
  google_artifact_registry_repository.docker \
  "projects/${PROJECT_ID}/locations/${REGION}/repositories/${REPOSITORY_ID}" || true

echo "== terraform import: Cloud Run service =="
terraform import -var-file=terraform.tfvars \
  google_cloud_run_service.app \
  "locations/${REGION}/namespaces/${PROJECT_ID}/services/${SERVICE_NAME}" || true

echo "== terraform import: Public invoker IAM =="
terraform import -var-file=terraform.tfvars \
  google_cloud_run_service_iam_member.public_invoker \
  "v1/projects/${PROJECT_ID}/locations/${REGION}/services/${SERVICE_NAME} roles/run.invoker allUsers" || true

echo "== terraform plan (post-import) =="
terraform plan -var-file=terraform.tfvars
