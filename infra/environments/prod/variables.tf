variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "google_access_token" {
  description = "Optional short-lived access token for Google provider auth"
  type        = string
  default     = ""
  sensitive   = true
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "orderflow-app"
}

variable "artifact_repository_id" {
  description = "Artifact Registry repository id"
  type        = string
  default     = "my-repo"
}

variable "migrate_job_name" {
  description = "Cloud Run job for migrations"
  type        = string
  default     = "orderflow-migrate"
}

variable "migrate_job_timeout" {
  description = "Cloud Run job timeout in seconds"
  type        = number
  default     = 1200
}

variable "enable_migrate_job" {
  description = "Create Cloud Run migration job resource"
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Container image URI for Cloud Run deployments"
  type        = string
  default     = "us-central1-docker.pkg.dev/orderflow-451220/my-repo/my-app"
}

variable "service_account_email" {
  description = "Service account used by Cloud Run service"
  type        = string
  default     = "841559594474-compute@developer.gserviceaccount.com"
}

variable "container_cpu_limit" {
  description = "Cloud Run CPU limit"
  type        = string
  default     = "1000m"
}

variable "container_memory_limit" {
  description = "Cloud Run memory limit"
  type        = string
  default     = "512Mi"
}

variable "container_concurrency" {
  description = "Cloud Run request concurrency"
  type        = number
  default     = 80
}

variable "max_instances" {
  description = "Cloud Run max instances"
  type        = number
  default     = 100
}

variable "public_invoker_member" {
  description = "IAM member for public invocation"
  type        = string
  default     = "allUsers"
}

variable "manage_secret_versions" {
  description = "Whether Terraform should create/update secret versions"
  type        = bool
  default     = false
}

variable "secret_values" {
  description = "Secret values for initial bootstrap; keep only in local tfvars."
  type = object({
    django_secret_key  = string
    database_url       = string
    telegram_bot_token = string
  })
  default = {
    django_secret_key  = ""
    database_url       = ""
    telegram_bot_token = ""
  }
  sensitive = true
}

variable "labels" {
  description = "Extra labels applied to supported resources"
  type        = map(string)
  default     = {}
}

variable "github_repository" {
  description = "GitHub repository in owner/name format allowed to use WIF"
  type        = string
  default     = "mykyyta/order-flow"
}

variable "wif_pool_id" {
  description = "Workload Identity Pool ID"
  type        = string
  default     = "github-actions-pool"
}

variable "wif_provider_id" {
  description = "Workload Identity Provider ID"
  type        = string
  default     = "github-actions-provider"
}

variable "terraform_deployer_sa_id" {
  description = "Service account ID used by GitHub Actions Terraform deploy"
  type        = string
  default     = "orderflow-tf-deployer"
}

variable "tf_state_bucket_name" {
  description = "GCS bucket name used for Terraform remote state"
  type        = string
  default     = "orderflow-451220-tfstate"
}

variable "terraform_deployer_project_roles" {
  description = "Project roles granted to Terraform deployer SA"
  type        = set(string)
  default = [
    "roles/run.admin",
    "roles/artifactregistry.admin",
    "roles/secretmanager.admin",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/storage.admin",
  ]
}
