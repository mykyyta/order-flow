output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "Primary GCP region"
  value       = var.region
}

output "artifact_repository" {
  description = "Artifact Registry repository id"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_service.app.name
}

output "cloud_run_service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.app.status[0].url
}

output "terraform_deployer_service_account_email" {
  description = "Service account for GitHub Actions Terraform deploy"
  value       = google_service_account.terraform_deployer.email
}

output "github_wif_provider_name" {
  description = "Full WIF provider resource name for GitHub OIDC auth"
  value       = google_iam_workload_identity_pool_provider.github_actions.name
}
