"""
Celery tasks — งานอัตโนมัติฝั่งวัตถุดิบ/จัดซื้อ
(ตรรกะอยู่ใน services.py — task เป็นแค่ wrapper ให้ Celery beat เรียก)
"""
from celery import shared_task

from django.core.management import call_command


@shared_task(name='restaurant.run_daily_automation')
def run_daily_automation_task(expiry_days=3):
    """เรียก management command ตัวเดียวกับ Render Cron — single source of truth"""
    call_command('run_daily_automation', expiry_days=expiry_days)
    return 'ok'
