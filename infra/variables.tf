variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region for Cloud Run resources"
  type        = string
  default     = "australia-southeast1"
}

variable "gke_zone" {
  description = "Zone containing the MIM GKE cluster"
  type        = string
  default     = "australia-southeast1-a"
}

variable "real_execution" {
  description = "Enable controlled live GKE execution"
  type        = bool
  default     = false
}

variable "gke_worker_nodes" {
  description = "Number of GKE worker nodes for the demo"
  type        = number
  default     = 0

  validation {
    condition     = var.gke_worker_nodes >= 0 && var.gke_worker_nodes <= 1
    error_message = "gke_worker_nodes must be either 0 or 1 for this demo."
  }
}

variable "mim_api_image" {
  description = "Fully qualified container image for the MIM FastAPI service"
  type        = string
}
