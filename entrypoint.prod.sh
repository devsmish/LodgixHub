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

# 2. Superuser creation — only runs on first deploy while
#    DJANGO_SUPERUSER_* vars are set; safe to leave, idempotent check inside.
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "=== Checking and creating a superuser ==="
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()

email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'

if not User.objects.filter(email=email).exists():
    extra_fields = {}
    if 'nickname' in User.REQUIRED_FIELDS:
        extra_fields['nickname'] = '$DJANGO_SUPERUSER_NICKNAME'
    User.objects.create_superuser(email=email, password=password, **extra_fields)
    print('Superuser successfully created!')
else:
    print('The superuser already exists.')
"
fi

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

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
