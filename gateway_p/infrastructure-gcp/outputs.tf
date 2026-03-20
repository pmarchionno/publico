# =============================================================================
# Outputs - PagoFlex Infrastructure
# =============================================================================

# =============================================================================
# Cloud Run
# =============================================================================

output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "api_service_name" {
  description = "Cloud Run API service name"
  value       = google_cloud_run_v2_service.api.name
}

# =============================================================================
# Database
# =============================================================================

output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "database_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_url" {
  description = "Database connection URL (without password)"
  value       = "postgresql+asyncpg://${var.db_user}:****@${google_sql_database_instance.postgres.private_ip_address}:5432/pagoflex"
  sensitive   = false
}

# =============================================================================
# Redis
# =============================================================================

output "redis_internal_ip" {
  description = "Redis server internal IP address"
  value       = google_compute_address.redis_internal_ip.address
}

output "redis_instance_name" {
  description = "Redis Compute Engine instance name"
  value       = google_compute_instance.redis.name
}

output "redis_url" {
  description = "Redis connection URL (without password)"
  value       = "redis://****@${google_compute_address.redis_internal_ip.address}:6379/0"
  sensitive   = false
}

# =============================================================================
# Networking
# =============================================================================

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "vpc_connector_name" {
  description = "VPC Access Connector name"
  value       = google_vpc_access_connector.connector.name
}

output "subnet_name" {
  description = "Subnet name"
  value       = google_compute_subnetwork.subnet.name
}

# =============================================================================
# VPN (Banco de Comercio)
# =============================================================================

output "vpn_gateway_name" {
  description = "HA VPN Gateway name (for gcloud describe)"
  value       = google_compute_ha_vpn_gateway.vpn_gateway.name
}

output "vpn_gateway_public_ip" {
  description = "VPN Gateway public IP - use as 'IP Peer' in bank VPN form"
  value       = length(google_compute_ha_vpn_gateway.vpn_gateway.vpn_interfaces) > 0 ? google_compute_ha_vpn_gateway.vpn_gateway.vpn_interfaces[0].ip_address : null
}

output "vpn_tunnel_name" {
  description = "VPN tunnel name"
  value       = google_compute_vpn_tunnel.bank_tunnel.name
}

output "vpn_local_networks" {
  description = "Local networks to give to bank as 'Tráfico Interesante'"
  value       = "10.0.0.0/24, 10.8.0.0/28"
}

output "vpn_shared_secret_secret_name" {
  description = "Secret Manager secret name for VPN pre-shared key (consult to pass to bank)"
  value       = google_secret_manager_secret.vpn_shared_secret.secret_id
}

output "vpn_shared_secret_retrieve_command" {
  description = "Command to retrieve VPN shared secret for the bank"
  value       = "gcloud secrets versions access latest --secret=${google_secret_manager_secret.vpn_shared_secret.secret_id} --project=${var.project_id}"
}

# =============================================================================
# Artifact Registry
# =============================================================================

output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pagoflex.repository_id}"
}

# =============================================================================
# Service Account
# =============================================================================

output "cloudrun_service_account" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloudrun.email
}

# =============================================================================
# Useful Commands
# =============================================================================

output "helpful_commands" {
  description = "Helpful commands for deployment"
  value = {
    build_and_push = "docker build -t ${var.region}-docker.pkg.dev/${var.project_id}/${var.project_name}/${var.project_name}:latest . && docker push ${var.region}-docker.pkg.dev/${var.project_id}/${var.project_name}/${var.project_name}:latest"
    run_migrations = "gcloud run jobs execute ${var.project_name}-migrations --region ${var.region}"
    run_worker     = "gcloud run jobs execute ${var.project_name}-worker --region ${var.region}"
    ssh_to_redis   = "gcloud compute ssh ${var.project_name}-redis --zone ${var.region}-a --tunnel-through-iap"
    view_logs      = "gcloud run services logs read ${var.project_name}-api --region ${var.region}"
  }
}
