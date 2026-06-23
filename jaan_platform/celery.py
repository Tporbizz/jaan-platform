"""
Celery configuration for Jaan Platform.
งานอัตโนมัติทั้งหมดถูกเขียนเป็น management command (run_daily_automation)
Celery beat เป็นแค่ตัวตั้งเวลาเรียก — ระบบยังทำงานได้แม้ไม่มี Redis
(ใช้ Render Cron แทน) จึงไม่ผูกตายกับ Celery
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaan_platform.settings.development')

app = Celery('jaan_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ตารางเวลา — รันงานอัตโนมัติประจำวัน ตี 5 ตามเวลาไทย
app.conf.beat_schedule = {
    'daily-automation-0500': {
        'task': 'restaurant.run_daily_automation',
        'schedule': crontab(hour=5, minute=0),
    },
}
