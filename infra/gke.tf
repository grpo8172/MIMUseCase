resource "google_container_cluster" "mim" {
  name     = "mim-demo-cluster"
  location = "australia-southeast1-a"

  remove_default_node_pool = true
  initial_node_count       = 1
}

resource "google_container_node_pool" "default" {
  name       = "default-pool"
  cluster    = google_container_cluster.mim.name
  location   = google_container_cluster.mim.location
  node_count = var.real_execution ? 1 : var.gke_worker_nodes

  node_config {
    machine_type    = "e2-small"
    service_account = google_service_account.gke_nodes.email

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}