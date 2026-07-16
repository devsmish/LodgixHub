#!/bin/sh

# Stop the script on any error.
set -e

# 1. Waiting for MySQL to be ready (using the system utility netcat 'nc')
echo "=== Waiting for MySQL database ==="
python -c "
import socket
import time
import os

host = os.environ.get('MYSQL_HOST', 'db')
port = int(os.environ.get('MYSQL_PORT', 3306))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)

while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        time.sleep(0.5)
"
echo "The database is ready for use!"

echo "=== Using Django Migrations ==="
python manage.py migrate

# 2. Automatic creation of a superuser
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "=== Checking and creating a superuser ==="
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()

email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'

# Searching for a user by email
if not User.objects.filter(email=email).exists():
    extra_fields = {}

    # If the nickname is mandatory, we pass it by default.
    if 'nickname' in User.REQUIRED_FIELDS:
        extra_fields['nickname'] = '$DJANGO_SUPERUSER_NICKNAME'

    User.objects.create_superuser(email=email, password=password, **extra_fields)
    print('Superuser successfully created!')
else:
    print('The superuser already exists.')
"
fi

echo "=== Building static files (for deployment) ==="
python manage.py collectstatic --noinput

echo "=== Starting the Django server ==="
exec python manage.py runserver 0.0.0.0:8000

# gunicorn server:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"