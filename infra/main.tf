data "google_client_config" "default" {}

data "google_container_cluster" "mim_existing" {
  project  = var.project_id
  name     = google_container_cluster.mim.name
  location = var.gke_zone
}

provider "kubernetes" {
  host = "https://${data.google_container_cluster.mim_existing.endpoint}"

  token = data.google_client_config.default.access_token

  cluster_ca_certificate = base64decode(
    data.google_container_cluster.mim_existing.master_auth[0].cluster_ca_certificate
  )
}