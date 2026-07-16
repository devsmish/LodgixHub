#!/bin/sh

# Останавливаем скрипт при любой ошибке
set -e

# 1. Ожидаем готовность MySQL (используем системную утилиту netcat 'nc')
echo "=== Ожидание базы данных MySQL ==="
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
echo "База данных готова к работе!"

echo "=== Применение миграций Django ==="
python manage.py migrate

# 2. Автоматическое создание суперпользователя (безопасное и адаптированное под твой User)
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "=== Проверка и создание суперпользователя ==="
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()

email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'

# Ищем по email, так как поля username в модели нет
if not User.objects.filter(email=email).exists():
    extra_fields = {}

    # Если nickname обязателен в твоей модели, передаем его по умолчанию
    if 'nickname' in User.REQUIRED_FIELDS:
        extra_fields['nickname'] = '$DJANGO_SUPERUSER_NICKNAME'

    User.objects.create_superuser(email=email, password=password, **extra_fields)
    print('Суперпользователь успешно создан!')
else:
    print('Суперпользователь уже существует.')
"
fi

echo "=== Сборка статических файлов (для деплоя) ==="
python manage.py collectstatic --noinput

echo "=== Запуск сервера Django ==="
exec python manage.py runserver 0.0.0.0:8000