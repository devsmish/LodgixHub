#!/bin/sh

# Stop the script on any error.
set -e

# 1. Waiting for the database (RDS) to be ready
echo "=== Waiting for the database ==="
python -c "
import socket
import time
import os

host = os.environ.get('MYSQL_HOST')
port = int(os.environ.get('MYSQL_PORT', 3306))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)

while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        print(f'Waiting for {host}:{port}...')
        time.sleep(1)
"
echo "The database is ready for use!"

echo "=== Applying Django migrations ==="
python manage.py migrate --noinput

# Note: суперюзер не создаётся здесь — БД в проде восстанавливается
# из дампа (см. Этап 6), суперюзер там уже есть.

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

# Elastic IP недоступен (нет прав в учебном аккаунте) — публичный IP EC2
# меняется при каждом stop/start. Спрашиваем его у самого инстанса через
# IMDSv2 и добавляем в ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS на этот запуск,
# чтобы не редактировать .env.aws руками перед каждой демонстрацией.
echo "=== Detecting current public IP (IMDSv2) ==="
IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true)

if [ -n "$IMDS_TOKEN" ]; then
    CURRENT_PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
        http://169.254.169.254/latest/meta-data/public-ipv4 || true)
fi

if [ -n "$CURRENT_PUBLIC_IP" ]; then
    echo "Detected public IP: $CURRENT_PUBLIC_IP"
    export ALLOWED_HOSTS="${ALLOWED_HOSTS},${CURRENT_PUBLIC_IP}"
    export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS},http://${CURRENT_PUBLIC_IP}"
else
    echo "WARNING: could not detect public IP via IMDS — falling back to .env.aws values only"
fi

echo "=== Starting gunicorn ==="
exec gunicorn config.wsgi:application \
    --workers "${GUNICORN_WORKERS:-2}" \
    --worker-class sync \
    --bind 0.0.0.0:8000 \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
