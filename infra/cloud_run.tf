resource "google_cloud_run_v2_service" "mim_api" {
  name     = "mim-api"
  location = var.region

  deletion_protection = true

  template {
    service_account = google_service_account.mim_runtime.email

    containers {
      image = var.mim_api_image

      env {
        name  = "REAL_EXECUTION"
        value = "false"
      }

      env {
        name  = "USE_MONGO_MCP"
        value = "false"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GKE_CLUSTER_NAME"
        value = "mim-demo-cluster"
      }

      env {
        name  = "GKE_CLUSTER_LOCATION"
        value = var.gke_zone
      }
    }
  }
}