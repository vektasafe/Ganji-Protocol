#!/bin/bash
# Setup script for hybrid stack development

set -e

echo "Setting up Ganji Protocol Hybrid Stack..."

# 1. Create .env if it doesn't exist
if [ ! -f go-service/.env ]; then
  echo "Creating go-service/.env from template..."
  cp go-service/.env.example go-service/.env
fi

# 2. Check if Docker is available
if ! command -v docker &> /dev/null; then
  echo "Docker not found. Please install Docker."
  exit 1
fi

# 3. Start Docker containers
echo "Starting Docker containers (PostgreSQL + Go service)..."
docker-compose up -d

# 4. Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# 5. Run migrations
echo "Running database migrations..."
docker exec ganji-postgres psql -U ganji -d ganji_protocol -f /docker-entrypoint-initdb.d/001_initial_schema.sql || true

# 6. Check Go service health
echo "Checking Go service health..."
sleep 3
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
  echo "✓ Go service is healthy"
else
  echo "✗ Go service health check failed. Check logs: docker logs ganji-service"
fi

echo "Setup complete!"
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Go API: http://localhost:8080"
echo "  - Health: http://localhost:8080/health"
