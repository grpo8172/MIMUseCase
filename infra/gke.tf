resource "google_container_cluster" "mim" {
  name     = "mim-demo-cluster"
  location = var.gke_zone

  # Match the manually created cluster.
  initial_node_count = 0

  lifecycle {
    prevent_destroy = true
  }
}

# Existing manually created pool.
# Keep its immutable configuration aligned with the real resource.
resource "google_container_node_pool" "default" {
  name     = "default-pool"
  cluster  = google_container_cluster.mim.name
  location = var.gke_zone

  lifecycle {
    prevent_destroy = true

    # Preserve the manually created pool during the migration.
    ignore_changes = [
      node_config[0].service_account,
      node_config[0].oauth_scopes,
    ]
  }
}

# New Terraform-managed pool used by approved remediation workflows.
resource "google_container_node_pool" "remediation" {
  name     = "mim-remediation-pool"
  cluster  = google_container_cluster.mim.name
  location = var.gke_zone

  autoscaling {
    min_node_count = 0
    max_node_count = 1
  }

  node_config {
    machine_type    = "e2-small"
    service_account = google_service_account.gke_nodes.email

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "kubernetes_namespace_v1" "client_a_uat" {
  metadata {
    name = "client-a-uat"
  }
}