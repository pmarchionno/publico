# PagoFlex - Google Cloud Infrastructure

Terraform configuration for deploying PagoFlex to Google Cloud Platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Google Cloud                              │
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │   Cloud Run      │         │     Compute Engine           │  │
│  │   (API + Worker) │◄───────▶│     e2-medium (Ubuntu)        │  │
│  │   cpu-idle=false │   VPC   │     ┌──────────────────┐     │  │
│  └────────┬─────────┘ Connector│     │  Docker + Redis  │     │  │
│           │                    │     │     7-alpine     │     │  │
│           │                    │     │  (Persistent Disk)│    │  │
│           │                    │     └──────────────────┘     │  │
│           │                    └──────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │    Cloud SQL     │                                           │
│  │   PostgreSQL 15  │                                           │
│  │    (1 vCPU)      │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Google Cloud SDK** installed and configured
2. **Terraform** >= 1.0
3. **Docker** for building images

## Quick Start

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project pagoflex-middleware
```

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Initialize and Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 4. Build and Push Docker Image

```bash
# Set project (if not already set)
gcloud config set project pagoflex-middleware

# Authenticate Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build image with correct platform (required for Mac/ARM)
# From project root directory
docker build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest .

# Push image to Artifact Registry
docker push us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest

# Update Cloud Run with new image
cd infrastructure-gcp
terraform apply -var="api_image=us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest"
```

**Note for Mac users**: Always use `--platform linux/amd64` when building images, as Cloud Run requires amd64 architecture.

### 5. Run Database Migrations

```bash
gcloud run jobs execute pagoflex-migrations --region us-central1
```

## Resources Created

| Resource | Type | Description |
|----------|------|-------------|
| `pagoflex-vpc` | VPC Network | Private network |
| `pagoflex-subnet` | Subnet | 10.0.0.0/24 |
| `pagoflex-connector` | VPC Connector | Cloud Run → VPC |
| `pagoflex-db` | Cloud SQL | PostgreSQL 15, 1 vCPU |
| `pagoflex-redis` | Compute Engine | e2-medium, Ubuntu 22.04, Docker, Redis 7 (persistent disk) |
| `pagoflex-api` | Cloud Run Service | API with cpu-idle=false |
| `pagoflex-migrations` | Cloud Run Job | Alembic migrations |
| `pagoflex-worker` | Cloud Run Job | Celery worker |
| `pagoflex-vpn-gateway` | HA VPN Gateway | Site-to-site VPN with Banco de Comercio |
| `pagoflex-bank-tunnel` | VPN Tunnel | IPsec tunnel to bank Fortigate |

## VPN (Banco de Comercio)

A site-to-site VPN is created for integration with Banco de Comercio. The VPN pre-shared key is **generated automatically** by Terraform and stored in Secret Manager (so you can retrieve it later to pass to the bank). If you previously had `vpn_shared_secret` in `terraform.tfvars`, remove it.

### 1. Get values for the bank VPN form

After applying, run:

```bash
terraform output vpn_gateway_public_ip   # → IP Peer (give to bank)
terraform output vpn_local_networks      # → Tráfico Interesante: 10.0.0.0/24, 10.8.0.0/28
```

- **IP Peer**: Output `vpn_gateway_public_ip` (or get via `gcloud compute vpn-gateways describe pagoflex-middleware-vpn-gateway --region us-central1 --format='value(vpnInterfaces[0].ipAddress)'`).
- **Tráfico Interesante**: `10.0.0.0/24, 10.8.0.0/28`
- **URL servicio de healthcheck**: Your internal health URL (e.g. Internal LB or VM in VPC) reachable at an IP in the above ranges.

### 2. Retrieve the VPN shared secret (to pass to the bank)

The pre-shared key is stored in Secret Manager. After `terraform apply`:

```bash
# Option 1: Use the output command
terraform output -raw vpn_shared_secret_retrieve_command | sh

# Option 2: Run gcloud directly (replace PROJECT and SECRET name from terraform output)
gcloud secrets versions access latest --secret=pagoflex-middleware-vpn-shared-secret --project=YOUR_PROJECT_ID
```

Give this value to the bank so they can configure their Fortigate with the same pre-shared key.

### 3. Bank-side configuration

The bank configures their Fortigate (190.210.90.196) with:

- Peer IP = your VPN gateway public IP
- Remote network = 10.0.0.0/24, 10.8.0.0/28
- Pre-shared key = value retrieved from Secret Manager (see step 2)

### 4. Optional variables

In `terraform.tfvars` you can override (the shared secret is auto-generated and stored in Secret Manager):

```hcl
vpn_peer_ip             = "190.210.90.196"   # Bank Fortigate IP (default)
vpn_remote_network_cidr = "192.168.86.0/24" # Bank network (default)
vpn_ike_version         = 2                   # IKEv2 (default)
```

## Cost Estimate (Monthly)

| Resource | Estimated Cost |
|----------|----------------|
| Cloud SQL (1 vCPU) | ~$25 |
| Compute Engine (e2-medium) | ~$24 |
| Cloud Run (min 0 instances) | ~$0-30 (usage based) |
| VPC Connector | ~$7 |
| **Total** | **~$56-86/month** |

## Environment Variables

The following environment variables are automatically configured in Cloud Run:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

## Docker Build and Deployment

### Complete Deployment Script

Create a `deploy.sh` script in the project root:

```bash
#!/bin/bash
set -e

PROJECT_ID="pagoflex-middleware"
REGION="us-central1"
REPO_NAME="pagoflex-middleware"
IMAGE_NAME="pagoflex"
TAG="latest"

FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}"

echo "🔐 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

echo "🔐 Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo "🏗️  Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t ${FULL_IMAGE_NAME} .

echo "📤 Pushing image to Artifact Registry..."
docker push ${FULL_IMAGE_NAME}

echo "🔄 Updating Cloud Run..."
cd infrastructure-gcp
terraform apply -var="api_image=${FULL_IMAGE_NAME}" -auto-approve

echo "✅ Deployment complete!"
echo "🌐 API URL: $(terraform output -raw api_url)"
```

Make it executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

### Manual Commands

```bash
# 1. Set GCP project
gcloud config set project pagoflex-middleware

# 2. Authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# 3. Build image (from project root)
docker build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest .

# 4. Push image
docker push us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest

# 5. Update Cloud Run
cd infrastructure-gcp
terraform apply -var="api_image=us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware/pagoflex:latest"
```

## Useful Commands

```bash
# View API logs
gcloud run services logs read pagoflex-middleware-api --region us-central1

# SSH to Redis instance (via IAP)
gcloud compute ssh pagoflex-middleware-redis --zone us-central1-a --tunnel-through-iap

# Once connected to Redis instance:
# Check Redis container status
docker ps
docker logs redis

# Restart Redis
cd /opt/redis && docker compose restart

# View Redis data
ls -lh /opt/redis/data

# Execute worker job
gcloud run jobs execute pagoflex-middleware-worker --region us-central1

# Execute migrations
gcloud run jobs execute pagoflex-middleware-migrations --region us-central1

# Scale Cloud Run
gcloud run services update pagoflex-middleware-api --region us-central1 --max-instances=20

# View Artifact Registry images
gcloud artifacts docker images list us-central1-docker.pkg.dev/pagoflex-middleware/pagoflex-middleware
```

## Redis Configuration

The Redis instance runs on Compute Engine with:
- **OS**: Ubuntu 22.04 LTS
- **Docker**: Installed automatically via startup script
- **Persistent Storage**: 20GB SSD disk mounted at `/opt/redis/data`
- **Auto-start**: Systemd service ensures Redis starts on boot
- **Data Persistence**: AOF (Append Only File) enabled

The startup script (`scripts/install-docker.sh`) automatically:
1. Formats and mounts the persistent disk
2. Installs Docker and Docker Compose
3. Creates and starts the Redis container
4. Configures auto-start on boot

## Cost Optimization Scripts

To save costs when the infrastructure is not in use, you can stop Compute Engine and Cloud SQL instances:

### Stop Infrastructure (Save Costs)

```bash
# Stop Compute Engine and Cloud SQL
./scripts/stop-infrastructure.sh
```

This will:
- Stop the Compute Engine instance (Redis VM)
- Stop the Cloud SQL instance (PostgreSQL)
- **Estimated savings**: ~$0.06/hour (~$1.44/day) when stopped

### Start Infrastructure (Resume Service)

```bash
# Start Compute Engine and Cloud SQL
./scripts/start-infrastructure.sh
```

This will:
- Start the Cloud SQL instance (takes 1-2 minutes)
- Start the Compute Engine instance (takes 30-60 seconds)
- Wait for services to be ready

**Note**: Cloud Run services will automatically start when they receive traffic, but they won't be able to connect to Redis or PostgreSQL until you start those services.

### Usage Tips

- **Development**: Stop infrastructure when not working to save costs
- **Production**: Keep infrastructure running 24/7
- **Scheduled**: Use Cloud Scheduler to automatically start/stop at specific times

## Cleanup

```bash
# Destroy all resources
terraform destroy
```

⚠️ **Warning**: If you need to protect Cloud SQL from accidental deletion, set `deletion_protection = true` in `main.tf`.
