"""
ดึงข้อมูลจาก Sensibo Sky API — รัน hourly ผ่าน cron/celery
คำนวณ estimated electricity cost แล้วบันทึก ACUsageLog
"""
import requests
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Tenant
from reports.models import ACUsageLog


# ค่าไฟเฉลี่ย (บาท/kWh) — TOU rate ประมาณ
ELECTRICITY_RATE = Decimal('4.5')


class Command(BaseCommand):
    help = 'Fetch Sensibo Sky data and log AC usage + estimated cost'

    def handle(self, *args, **options):
        api_key = getattr(settings, 'SENSIBO_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.WARNING(
                'No SENSIBO_API_KEY — add to .env to enable AC tracking'
            ))
            return

        try:
            # Get all pods
            resp = requests.get(
                'https://home.sensibo.com/api/v2/users/me/pods',
                params={'apiKey': api_key, 'fields': 'id,room,measurements,acState'},
                timeout=15,
            )
            resp.raise_for_status()
            pods = resp.json().get('result', [])
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Sensibo API error: {e}'))
            return

        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('No tenant found'))
            return

        now = timezone.now()
        for pod in pods:
            device_id = pod.get('id', '')
            measurements = pod.get('measurements', {})
            ac_state = pod.get('acState', {})

            temp = measurements.get('temperature', 0)
            humidity = measurements.get('humidity', 0)
            ac_on = ac_state.get('on', False)

            # Estimate power based on AC being on
            # Typical split AC: 1000-2000W when running
            power_w = Decimal('1500') if ac_on else Decimal('5')

            # Cost for 1 hour at this power
            cost = (power_w / Decimal('1000')) * ELECTRICITY_RATE

            ACUsageLog.objects.create(
                tenant=tenant,
                device_id=device_id,
                timestamp=now,
                power_watts=power_w,
                temperature=Decimal(str(temp)),
                humidity=Decimal(str(humidity)),
                ac_on=ac_on,
                estimated_cost_thb=cost,
            )

            self.stdout.write(
                f'  {device_id}: {temp}C, {"ON" if ac_on else "OFF"}, '
                f'{power_w}W, est cost: {cost} THB/hr'
            )

        self.stdout.write(self.style.SUCCESS(f'Logged {len(pods)} AC devices'))
