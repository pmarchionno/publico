#!/bin/bash
# =============================================================================
# Start Infrastructure Script
# =============================================================================
# This script starts Compute Engine and Cloud SQL instances to resume service
# Usage: ./start-infrastructure.sh
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load variables from terraform.tfvars if it exists
if [ -f "terraform.tfvars" ]; then
    PROJECT_ID=$(grep "^project_id" terraform.tfvars | cut -d'"' -f2)
    PROJECT_NAME=$(grep "^project_name" terraform.tfvars | cut -d'"' -f2)
    REGION=$(grep "^region" terraform.tfvars | cut -d'"' -f2)
else
    # Defaults (update these if terraform.tfvars doesn't exist)
    PROJECT_ID="pagoflex-middleware"
    PROJECT_NAME="pagoflex-middleware"
    REGION="us-central1"
fi

ZONE="${REGION}-a"
REDIS_INSTANCE="${PROJECT_NAME}-redis"
DB_INSTANCE="${PROJECT_NAME}-db"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting Infrastructure${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# =============================================================================
# Start Cloud SQL Instance
# =============================================================================
echo -e "${YELLOW}[1/2] Starting Cloud SQL instance: $DB_INSTANCE${NC}"
gcloud sql instances patch $DB_INSTANCE \
    --activation-policy=ALWAYS \
    --project=$PROJECT_ID \
    --quiet

echo -e "${GREEN}✓ Cloud SQL instance is starting...${NC}"
echo "   Waiting for Cloud SQL to be ready (this may take 1-2 minutes)..."

# Wait for Cloud SQL to be ready
RETRY_COUNT=0
MAX_RETRIES=30
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATUS" = "RUNNABLE" ]; then
        echo -e "${GREEN}✓ Cloud SQL is ready!${NC}"
        break
    fi
    echo "   Status: $STATUS (waiting...)"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}⚠ Warning: Cloud SQL may still be starting. Check manually.${NC}"
fi

# =============================================================================
# Start Compute Engine Instance (Redis)
# =============================================================================
echo ""
echo -e "${YELLOW}[2/2] Starting Compute Engine instance: $REDIS_INSTANCE${NC}"
gcloud compute instances start $REDIS_INSTANCE \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --quiet

echo -e "${GREEN}✓ Compute Engine instance is starting...${NC}"
echo "   Waiting for VM to be ready (this may take 30-60 seconds)..."

# Wait for VM to be ready
RETRY_COUNT=0
MAX_RETRIES=20
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(gcloud compute instances describe $REDIS_INSTANCE --zone=$ZONE --project=$PROJECT_ID --format="value(status)" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATUS" = "RUNNING" ]; then
        echo -e "${GREEN}✓ Compute Engine is running!${NC}"
        break
    fi
    echo "   Status: $STATUS (waiting...)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}⚠ Warning: VM may still be starting. Check manually.${NC}"
fi

# =============================================================================
# Wait for Redis to be ready
# =============================================================================
echo ""
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
echo "   (This may take 1-2 minutes for Docker and Redis to start)"

sleep 30

# Try to check Redis status via SSH (optional, requires IAP)
echo "   You can verify Redis manually with:"
echo "   gcloud compute ssh $REDIS_INSTANCE --zone=$ZONE --tunnel-through-iap"
echo "   sudo docker ps"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Infrastructure Started Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Cloud SQL:"
echo "  Instance: $DB_INSTANCE"
echo "  Status: $(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format='value(state)' 2>/dev/null || echo 'Checking...')"
echo ""
echo "Compute Engine:"
echo "  Instance: $REDIS_INSTANCE"
echo "  Status: $(gcloud compute instances describe $REDIS_INSTANCE --zone=$ZONE --project=$PROJECT_ID --format='value(status)' 2>/dev/null || echo 'Checking...')"
echo ""
echo -e "${YELLOW}Note:${NC} Cloud Run services will automatically start when they receive traffic."
echo ""
