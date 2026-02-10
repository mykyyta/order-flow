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
  value       = try(google_artifact_registry_repository.docker[0].repository_id, null)
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
  value       = try(google_service_account.terraform_deployer[0].email, null)
}

output "github_wif_provider_name" {
  description = "Full WIF provider resource name for GitHub OIDC auth"
  value       = try(google_iam_workload_identity_pool_provider.github_actions[0].name, null)
}

output "custom_domain_mapping_records" {
  description = "DNS records to add for custom domain (after apply and domain verification)"
  value       = length(google_cloud_run_domain_mapping.app) > 0 ? google_cloud_run_domain_mapping.app[0].status[0].resource_records : []
}
