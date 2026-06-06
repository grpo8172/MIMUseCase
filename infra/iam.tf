resource "google_service_account" "mim_runtime" {
  project      = var.project_id
  account_id   = "mim-runtime"
  display_name = "MIM runtime service account"
}

resource "google_service_account" "gke_nodes" {
  project      = var.project_id
  account_id   = "mim-gke-nodes"
  display_name = "MIM GKE node service account"
}

resource "google_project_iam_member" "mim_cluster_viewer" {
  project = var.project_id
  role    = "roles/container.clusterViewer"
  member  = "serviceAccount:${google_service_account.mim_runtime.email}"
}

resource "google_project_iam_member" "gke_node_role" {
  project = var.project_id
  role    = "roles/container.defaultNodeServiceAccount"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "kubernetes_role_v1" "mim_remediator" {
  metadata {
    name      = "mim-remediator"
    namespace = kubernetes_namespace_v1.client_a_uat.metadata[0].name
  }

  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments"]
    verbs      = ["get", "list", "patch", "update"]
  }
}

resource "kubernetes_role_binding_v1" "mim_remediator" {
  metadata {
    name      = "mim-remediator"
    namespace = kubernetes_namespace_v1.client_a_uat.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.mim_remediator.metadata[0].name
  }

  subject {
    kind      = "User"
    name      = google_service_account.mim_runtime.email
    api_group = "rbac.authorization.k8s.io"
  }
}

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }

    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.gke_zone
}