# =============================================================================
# Variables - PagoFlex Infrastructure
# =============================================================================

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "pagoflex"
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "db_user" {
  description = "Database username"
  type        = string
  default     = "pagoflex"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# =============================================================================
# Redis Configuration
# =============================================================================

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

# =============================================================================
# Cloud Run Configuration
# =============================================================================

variable "api_image" {
  description = "Docker image for the API (e.g., gcr.io/project/pagoflex:latest)"
  type        = string
  default     = "gcr.io/cloudrun/hello"  # Placeholder, replace with actual image
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to Cloud Run API"
  type        = bool
  default     = false
}

# =============================================================================
# VPN Configuration (Banco de Comercio / Site-to-Site)
# =============================================================================

variable "vpn_peer_ip" {
  description = "Peer (bank) VPN gateway public IP address"
  type        = string
  default     = "190.210.90.196"
}

variable "vpn_remote_network_cidr" {
  description = "Remote (bank) network CIDR reachable via VPN"
  type        = string
  default     = "192.168.86.0/24"
}

variable "vpn_ike_version" {
  description = "IKE version for VPN tunnel (1 or 2)"
  type        = number
  default     = 2
}
