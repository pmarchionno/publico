# =============================================================================
# PagoFlex Infrastructure - Google Cloud Platform
# =============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# =============================================================================
# VPC Network
# =============================================================================

resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_name}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

# =============================================================================
# Cloud NAT for Internet Access
# =============================================================================

resource "google_compute_router" "router" {
  name    = "${var.project_name}-router"
  region  = var.region
  network = google_compute_network.vpc.id

  bgp {
    asn = 64514
  }
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }

  depends_on = [google_compute_router.router]
}

# =============================================================================
# VPC Connector for Cloud Run
# =============================================================================

resource "google_vpc_access_connector" "connector" {
  name          = "pagoflex-vpc-conn"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"
  
  min_instances = 2
  max_instances = 3
}

# =============================================================================
# Cloud SQL - PostgreSQL
# =============================================================================

resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-db"
  database_version = "POSTGRES_17"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = "db-custom-1-3840"  # 1 vCPU, 3.75 GB RAM
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "pagoflex" {
  name     = "pagoflex"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "pagoflex" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip_range" {
  name          = "${var.project_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# =============================================================================
# Compute Engine - Redis Server
# =============================================================================

resource "google_compute_address" "redis_internal_ip" {
  name         = "${var.project_name}-redis-ip"
  subnetwork   = google_compute_subnetwork.subnet.id
  address_type = "INTERNAL"
  region       = var.region
}

# Persistent disk for Redis data
resource "google_compute_disk" "redis_data" {
  name  = "${var.project_name}-redis-data"
  type  = "pd-ssd"
  zone  = "${var.region}-a"
  size  = 20
}

# Service Account for Redis instance
resource "google_service_account" "redis" {
  account_id   = "${var.project_name}-redis"
  display_name = "Redis Compute Engine Service Account"
}

resource "google_compute_instance" "redis" {
  name         = "${var.project_name}-redis"
  machine_type = "e2-medium"
  zone         = "${var.region}-a"

  tags = ["redis-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
      type  = "pd-ssd"
    }
  }

  # Attach persistent disk for Redis data
  attached_disk {
    source      = google_compute_disk.redis_data.id
    device_name = "redis-data"
  }

  network_interface {
    network    = google_compute_network.vpc.name
    subnetwork = google_compute_subnetwork.subnet.name
    network_ip = google_compute_address.redis_internal_ip.address
  }

  metadata_startup_script = templatefile("${path.module}/scripts/install-docker.sh", {
    REDIS_PASSWORD = var.redis_password
  })

  service_account {
    email  = google_service_account.redis.email
    scopes = ["cloud-platform"]
  }

  allow_stopping_for_update = true
}

# Firewall rule - Allow Redis from VPC Connector
resource "google_compute_firewall" "allow_redis" {
  name    = "${var.project_name}-allow-redis"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  source_ranges = ["10.8.0.0/28"]  # VPC Connector range
  target_tags   = ["redis-server"]
}

# Firewall rule - Allow SSH (for debugging)
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.project_name}-allow-ssh"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]  # IAP range
  target_tags   = ["redis-server"]
}

# =============================================================================
# Cloud VPN (Site-to-Site with Banco de Comercio)
# =============================================================================

resource "random_password" "vpn_shared_secret" {
  length  = 32
  special = true
}

resource "google_compute_ha_vpn_gateway" "vpn_gateway" {
  name    = "${var.project_name}-vpn-gateway"
  network = google_compute_network.vpc.id
  region  = var.region
}

resource "google_compute_external_vpn_gateway" "bank_gateway" {
  name            = "${var.project_name}-bank-gateway"
  redundancy_type = "SINGLE_IP_INTERNALLY_REDUNDANT"

  interface {
    id         = 0
    ip_address = var.vpn_peer_ip
  }
}

resource "google_compute_router" "vpn_router" {
  name    = "${var.project_name}-vpn-router"
  region  = var.region
  network = google_compute_network.vpc.id

  bgp {
    asn = 64515
  }
}

resource "google_compute_vpn_tunnel" "bank_tunnel" {
  name                            = "${var.project_name}-bank-tunnel"
  region                          = var.region
  vpn_gateway                     = google_compute_ha_vpn_gateway.vpn_gateway.id
  vpn_gateway_interface           = 0
  peer_external_gateway           = google_compute_external_vpn_gateway.bank_gateway.id
  peer_external_gateway_interface = 0
  shared_secret                   = random_password.vpn_shared_secret.result
  router                          = google_compute_router.vpn_router.id
  ike_version                     = var.vpn_ike_version
}

resource "google_compute_route" "vpn_route_to_bank" {
  name                = "${var.project_name}-route-to-bank"
  network             = google_compute_network.vpc.name
  dest_range          = var.vpn_remote_network_cidr
  priority            = 1000
  next_hop_vpn_tunnel = google_compute_vpn_tunnel.bank_tunnel.id
}

# Firewall rule - Allow traffic from bank network via VPN
resource "google_compute_firewall" "allow_vpn_from_bank" {
  name    = "${var.project_name}-allow-vpn-from-bank"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "5432", "6379"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.vpn_remote_network_cidr]
}

# =============================================================================
# Secret Manager
# =============================================================================

resource "google_secret_manager_secret" "vpn_shared_secret" {
  secret_id = "${var.project_name}-vpn-shared-secret"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "vpn_shared_secret" {
  secret      = google_secret_manager_secret.vpn_shared_secret.id
  secret_data = random_password.vpn_shared_secret.result
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.project_name}-db-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "redis_password" {
  secret_id = "${var.project_name}-redis-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_password" {
  secret      = google_secret_manager_secret.redis_password.id
  secret_data = var.redis_password
}

# =============================================================================
# Artifact Registry
# =============================================================================

resource "google_artifact_registry_repository" "pagoflex" {
  location      = var.region
  repository_id = var.project_name
  description   = "Docker repository for PagoFlex"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# =============================================================================
# Cloud Run Service - API
# =============================================================================

resource "google_cloud_run_v2_service" "api" {
  name     = "${var.project_name}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      name  = "api"
      image = var.api_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = false  # cpu-throttling = false
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_user}:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/pagoflex"
      }

      env {
        name  = "REDIS_URL"
        value = "redis://:${var.redis_password}@${google_compute_address.redis_internal_ip.address}:6379/0"
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 15
        timeout_seconds       = 3
        period_seconds        = 30
      }
    }

    service_account = google_service_account.cloudrun.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_sql_database_instance.postgres,
    google_compute_instance.redis,
    google_project_service.apis,
    google_artifact_registry_repository.pagoflex
  ]
}

# =============================================================================
# Cloud Run Job - Migrations
# =============================================================================

resource "google_cloud_run_v2_job" "migrations" {
  name     = "${var.project_name}-migrations"
  location = var.region

  template {
    template {
      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        name  = "migrations"
        image = var.api_image

        command = ["alembic"]
        args    = ["-c", "alembic.ini", "upgrade", "head"]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://${var.db_user}:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/pagoflex"
        }
      }

      service_account = google_service_account.cloudrun.email
      timeout         = "300s"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.pagoflex
  ]
}

# =============================================================================
# Cloud Run Job - Celery Worker
# =============================================================================

resource "google_cloud_run_v2_job" "worker" {
  name     = "${var.project_name}-worker"
  location = var.region

  template {
    template {
      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }

      containers {
        name  = "worker"
        image = var.api_image

        command = ["celery"]
        args    = ["-A", "app.scheduler.worker", "worker", "--loglevel=info"]

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://${var.db_user}:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/pagoflex"
        }

        env {
          name  = "REDIS_URL"
          value = "redis://:${var.redis_password}@${google_compute_address.redis_internal_ip.address}:6379/0"
        }
      }

      service_account = google_service_account.cloudrun.email
      timeout         = "3600s"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.pagoflex
  ]
}

# =============================================================================
# IAM - Service Account for Cloud Run
# =============================================================================

resource "google_service_account" "cloudrun" {
  account_id   = "${var.project_name}-cloudrun"
  display_name = "PagoFlex Cloud Run Service Account"
}

resource "google_project_iam_member" "cloudrun_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

resource "google_project_iam_member" "cloudrun_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Allow unauthenticated access to Cloud Run (for public API)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.allow_unauthenticated ? 1 : 0
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}
