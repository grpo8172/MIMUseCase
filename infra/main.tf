data "google_client_config" "default" {}

data "google_container_cluster" "mim_existing" {
  project  = var.project_id
  name     = google_container_cluster.mim.name
  location = var.gke_zone
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}