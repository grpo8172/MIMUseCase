resource "google_cloud_run_v2_service" "mim_api" {
  name     = "mim-api"
  location = var.region

  template {
    service_account = google_service_account.mim_runtime.email

    containers {
      image = var.mim_api_image

      env {
        name  = "REAL_EXECUTION"
        value = tostring(var.real_execution)
      }

      env {
        name  = "GKE_CLUSTER_NAME"
        value = google_container_cluster.mim.name
      }

      env {
        name  = "GKE_CLUSTER_LOCATION"
        value = var.gke_zone
      }

      env {
        name  = "GKE_NAMESPACE"
        value = "client-a-uat"
      }
    }
  }
}