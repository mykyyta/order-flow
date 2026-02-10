locals {
  name_prefix = "pult-${var.environment}"

  common_labels = merge(
    {
      app        = "pult"
      env        = var.environment
      managed_by = "terraform"
    },
    var.labels,
  )

  base_secrets = {
    django_secret_key = {
      secret_id = "${var.secret_id_prefix}-django-secret-key"
      value     = var.secret_values.django_secret_key
    }
    database_url = {
      secret_id = "${var.secret_id_prefix}-database-url"
      value     = var.secret_values.database_url
    }
  }
  secrets = merge(
    local.base_secrets,
    var.enable_telegram_bot_token_secret ? {
      telegram_bot_token = {
        secret_id = "${var.secret_id_prefix}-telegram-bot-token"
        value     = var.secret_values.telegram_bot_token
      }
    } : {}
  )

  secret_values_for_versions = var.manage_secret_versions ? {
    for key, cfg in local.secrets : key => cfg
    if trimspace(cfg.value) != ""
  } : {}
}

# Brownfield adoption mode:
# - Resources below are defined to be imported first.
# - `ignore_changes = all` avoids accidental drift fixes during first adoption.
# - After stable no-op plan, narrow ignore scope gradually.

resource "google_artifact_registry_repository" "docker" {
  count         = var.manage_shared_ci_resources ? 1 : 0
  location      = var.region
  repository_id = var.artifact_repository_id
  format        = "DOCKER"
  description   = "Pult container registry"
  labels        = local.common_labels

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_cloud_run_service" "app" {
  name     = var.service_name
  location = var.region

  metadata {
    labels = local.common_labels
  }

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"     = tostring(var.max_instances)
        "run.googleapis.com/startup-cpu-boost" = "true"
      }
    }

    spec {
      service_account_name  = var.service_account_email
      container_concurrency = var.container_concurrency

      containers {
        image = var.container_image

        env {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.prod"
        }
        env {
          name  = "ALLOWED_HOSTS"
          value = join(",", compact([".run.app", var.custom_domain]))
        }
        env {
          name = "DJANGO_SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.app["django_secret_key"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.app["database_url"].secret_id
              key  = "latest"
            }
          }
        }
        dynamic "env" {
          for_each = var.enable_telegram_bot_token_secret ? [1] : []
          content {
            name = "TELEGRAM_BOT_TOKEN"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.app["telegram_bot_token"].secret_id
                key  = "latest"
              }
            }
          }
        }
        dynamic "env" {
          for_each = var.enable_telegram_bot_token_secret ? [] : [1]
          content {
            name  = "TELEGRAM_BOT_TOKEN"
            value = ""
          }
        }

        resources {
          limits = {
            cpu    = var.container_cpu_limit
            memory = var.container_memory_limit
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  # Image is updated by deploy.yml (gcloud run services update). Terraform apply must not overwrite it.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [template]
  }
}

resource "google_cloud_run_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_service.app.name
  role     = "roles/run.invoker"
  member   = var.public_invoker_member

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_cloud_run_domain_mapping" "app" {
  count    = length(var.custom_domain) > 0 ? 1 : 0
  location = var.region
  name     = var.custom_domain

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_service.app.name
  }
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.secrets
  secret_id = each.value.secret_id
  labels    = local.common_labels

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_secret_manager_secret_version" "app" {
  for_each    = local.secret_values_for_versions
  secret      = google_secret_manager_secret.app[each.key].id
  secret_data = each.value.value
}

resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each  = google_secret_manager_secret.app
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}

resource "google_cloud_run_v2_job" "migrate" {
  count    = var.enable_migrate_job ? 1 : 0
  name     = var.migrate_job_name
  location = var.region

  labels = local.common_labels

  template {
    template {
      timeout     = "${var.migrate_job_timeout}s"
      max_retries = 0

      service_account = var.service_account_email

      containers {
        image   = var.container_image
        command = ["python", "src/manage.py", "migrate", "--noinput", "--fake-initial"]

        resources {
          limits = {
            cpu    = var.container_cpu_limit
            memory = var.container_memory_limit
          }
        }

        env {
          name = "DJANGO_SECRET_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["django_secret_key"].secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app["database_url"].secret_id
              version = "latest"
            }
          }
        }

        dynamic "env" {
          for_each = var.enable_telegram_bot_token_secret ? [1] : []
          content {
            name = "TELEGRAM_BOT_TOKEN"
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.app["telegram_bot_token"].secret_id
                version = "latest"
              }
            }
          }
        }
        dynamic "env" {
          for_each = var.enable_telegram_bot_token_secret ? [] : [1]
          content {
            name  = "TELEGRAM_BOT_TOKEN"
            value = ""
          }
        }

        env {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.prod"
        }
      }
    }
  }

  # Image is updated by deploy.yml (gcloud run jobs update). Terraform apply must not overwrite it.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [template]
  }

  depends_on = [google_secret_manager_secret_iam_member.runtime_access]
}

resource "google_service_account" "terraform_deployer" {
  count        = var.manage_shared_ci_resources ? 1 : 0
  account_id   = var.terraform_deployer_sa_id
  display_name = "Pult Terraform Deployer"
  description  = "Used by GitHub Actions via Workload Identity Federation"
}

resource "google_project_iam_member" "terraform_deployer_project_roles" {
  for_each = var.manage_shared_ci_resources ? var.terraform_deployer_project_roles : toset([])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${try(google_service_account.terraform_deployer[0].email, "")}"
}

resource "google_storage_bucket_iam_member" "terraform_deployer_state_bucket_access" {
  count  = var.manage_shared_ci_resources ? 1 : 0
  bucket = var.tf_state_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${try(google_service_account.terraform_deployer[0].email, "")}"
}

resource "google_service_account_iam_member" "terraform_deployer_runtime_sa_user" {
  count              = var.manage_shared_ci_resources ? 1 : 0
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${try(google_service_account.terraform_deployer[0].email, "")}"
}

resource "google_iam_workload_identity_pool" "github_actions" {
  count                     = var.manage_shared_ci_resources ? 1 : 0
  project                   = var.project_id
  workload_identity_pool_id = var.wif_pool_id
  display_name              = "GitHub Actions Pool"
  description               = "OIDC trust for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  count                              = var.manage_shared_ci_resources ? 1 : 0
  project                            = var.project_id
  workload_identity_pool_id          = try(google_iam_workload_identity_pool.github_actions[0].workload_identity_pool_id, var.wif_pool_id)
  workload_identity_pool_provider_id = var.wif_provider_id
  display_name                       = "GitHub Actions Provider"
  description                        = "Trusts token.actions.githubusercontent.com"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "assertion.repository=='${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_actions_wif_user" {
  count              = var.manage_shared_ci_resources ? 1 : 0
  service_account_id = try(google_service_account.terraform_deployer[0].name, "projects/${var.project_id}/serviceAccounts/${var.terraform_deployer_sa_id}@${var.project_id}.iam.gserviceaccount.com")
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${try(google_iam_workload_identity_pool.github_actions[0].name, "")}/attribute.repository/${var.github_repository}"
}

# Domain mapping is intentionally not managed yet to avoid accidental DNS route changes.
