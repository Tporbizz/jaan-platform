"""
Celery configuration for Jaan Platform.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaan_platform.settings.development')

app = Celery('jaan_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
