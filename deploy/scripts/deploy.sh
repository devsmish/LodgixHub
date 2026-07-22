#!/bin/bash
# start on the ec2-instance
set -e

echo "=== Pulling latest main ==="
git checkout main
git pull origin main

echo "=== Rebuilding images ==="
docker compose -f docker-compose.prod.yml build

echo "=== Recreating changed containers ==="
docker compose -f docker-compose.prod.yml up -d

echo "=== Status ==="
docker compose -f docker-compose.prod.yml ps

echo "=== Recent web logs (sanity check) ==="
docker compose -f docker-compose.prod.yml logs --tail=30 web
