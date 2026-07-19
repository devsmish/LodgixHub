import os
from celery import Celery

# Specify the default settings module for Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# All Celery settings will be read from `settings.py` with the `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically searches for tasks.py files within all installed apps.
app.autodiscover_tasks()
