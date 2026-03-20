#!/bin/bash
# =============================================================================
# Stop Infrastructure Script
# =============================================================================
# This script stops Compute Engine and Cloud SQL instances to save costs
# Usage: ./stop-infrastructure.sh
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

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Stopping Infrastructure${NC}"
echo -e "${YELLOW}========================================${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo -e "${RED}⚠ Warning: This will stop Compute Engine and Cloud SQL instances.${NC}"
echo -e "${RED}   Cloud Run services will not be able to connect until you start them again.${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# =============================================================================
# Stop Compute Engine Instance (Redis)
# =============================================================================
echo ""
echo -e "${YELLOW}[1/2] Stopping Compute Engine instance: $REDIS_INSTANCE${NC}"
gcloud compute instances stop $REDIS_INSTANCE \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --quiet

echo -e "${GREEN}✓ Compute Engine instance is stopping...${NC}"

# Wait for VM to be stopped
RETRY_COUNT=0
MAX_RETRIES=20
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(gcloud compute instances describe $REDIS_INSTANCE --zone=$ZONE --project=$PROJECT_ID --format="value(status)" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATUS" = "TERMINATED" ]; then
        echo -e "${GREEN}✓ Compute Engine is stopped!${NC}"
        break
    fi
    echo "   Status: $STATUS (stopping...)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}⚠ Warning: VM may still be stopping. Check manually.${NC}"
fi

# =============================================================================
# Stop Cloud SQL Instance
# =============================================================================
echo ""
echo -e "${YELLOW}[2/2] Stopping Cloud SQL instance: $DB_INSTANCE${NC}"
gcloud sql instances patch $DB_INSTANCE \
    --activation-policy=NEVER \
    --project=$PROJECT_ID \
    --quiet

echo -e "${GREEN}✓ Cloud SQL instance is stopping...${NC}"
echo "   (This may take 1-2 minutes)"

# Wait for Cloud SQL to be stopped
RETRY_COUNT=0
MAX_RETRIES=30
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATUS" = "SUSPENDED" ]; then
        echo -e "${GREEN}✓ Cloud SQL is stopped!${NC}"
        break
    fi
    echo "   Status: $STATUS (stopping...)"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}⚠ Warning: Cloud SQL may still be stopping. Check manually.${NC}"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Infrastructure Stopped Successfully!${NC}"
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
echo -e "${YELLOW}Cost Savings:${NC}"
echo "  - Compute Engine (e2-medium): ~\$0.03/hour saved"
echo "  - Cloud SQL (1 vCPU): ~\$0.03/hour saved"
echo "  - Total: ~\$0.06/hour (~\$1.44/day) when stopped"
echo ""
echo -e "${YELLOW}To restart, run:${NC} ./scripts/start-infrastructure.sh"
echo ""
