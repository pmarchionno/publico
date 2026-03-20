#!/bin/bash
# Install Docker and Docker Compose on Ubuntu
# Also mounts persistent disk for Redis data

set -e

# Mount persistent disk for Redis data
mkdir -p /opt/redis/data

# Check if disk is already formatted, if not format it
if ! blkid /dev/disk/by-id/google-redis-data > /dev/null 2>&1; then
  echo "Formatting persistent disk..."
  mkfs.ext4 -F /dev/disk/by-id/google-redis-data
fi

# Mount the disk
if ! mountpoint -q /opt/redis/data; then
  echo "Mounting persistent disk..."
  mount -o discard,defaults /dev/disk/by-id/google-redis-data /opt/redis/data
  # Add to fstab for auto-mount on boot
  if ! grep -q "google-redis-data" /etc/fstab; then
    echo '/dev/disk/by-id/google-redis-data /opt/redis/data ext4 defaults 0 2' >> /etc/fstab
  fi
fi

chmod 755 /opt/redis/data

# Update system
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Ensure Redis data directory has correct permissions
chown -R root:root /opt/redis/data
chmod 755 /opt/redis/data

# Create docker-compose.yml for Redis
mkdir -p /opt/redis
cat > /opt/redis/docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: always
    command: >
      redis-server 
      --appendonly yes 
      --maxmemory 2gb 
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/redis/data
COMPOSE_EOF

# Set permissions
chmod 644 /opt/redis/docker-compose.yml

# Create .env file for Redis password
cat > /opt/redis/.env << ENV_EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
ENV_EOF

chmod 600 /opt/redis/.env

# Start Redis with Docker Compose
cd /opt/redis
docker compose up -d

# Wait a bit and verify Redis is running
sleep 10
if docker ps | grep -q redis; then
  echo "Redis container started successfully"
  docker logs redis
else
  echo "Warning: Redis container may not be running"
  docker ps -a
fi

# Create systemd service to auto-start Redis on boot
cat > /etc/systemd/system/redis-docker.service << 'SERVICE_EOF'
[Unit]
Description=Redis Docker Container
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/redis
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable redis-docker.service
