"""
ตรวจสอบวัตถุดิบใกล้หมดอายุ — รัน daily ผ่าน cron
ส่ง Line Notify ถ้ามี LINENOTIFY_TOKEN ใน env
"""
import io
import sys
import requests
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from restaurant.models import LotBatch


class Command(BaseCommand):
    help = 'ตรวจสอบวัตถุดิบใกล้หมดอายุ แล้วส่งแจ้งเตือนผ่าน Line Notify'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=3,
            help='แจ้งเตือนถ้าหมดอายุภายใน N วัน (default: 3)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='แสดงผลเฉยๆ ไม่ส่ง Line Notify',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        today = timezone.localdate()
        cutoff = today + timedelta(days=days)

        # ของที่หมดอายุแล้ว
        expired = LotBatch.objects.filter(
            expiry_date__isnull=False,
            expiry_date__lt=today,
            quantity__gt=0,
        ).select_related('item', 'item__unit', 'tenant')

        # ของที่จะหมดอายุภายใน N วัน
        expiring = LotBatch.objects.filter(
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=cutoff,
            quantity__gt=0,
        ).select_related('item', 'item__unit', 'tenant')

        if not expired.exists() and not expiring.exists():
            self.stdout.write(self.style.SUCCESS('✅ ไม่มีวัตถุดิบใกล้หมดอายุ'))
            return

        # สร้างข้อความ
        lines = [f'🍽️ Jaan Expiry Alert — {today.strftime("%d/%m/%Y")}']
        lines.append('')

        if expired.exists():
            lines.append(f'🔴 หมดอายุแล้ว ({expired.count()} รายการ):')
            for lot in expired:
                lines.append(
                    f'  • {lot.item.name} — {lot.quantity} {lot.item.unit.abbreviation} '
                    f'(หมด {lot.expiry_date.strftime("%d/%m")})'
                )
            lines.append('')

        if expiring.exists():
            lines.append(f'🟠 จะหมดภายใน {days} วัน ({expiring.count()} รายการ):')
            for lot in expiring:
                days_left = (lot.expiry_date - today).days
                lines.append(
                    f'  • {lot.item.name} — {lot.quantity} {lot.item.unit.abbreviation} '
                    f'(อีก {days_left} วัน)'
                )

        message = '\n'.join(lines)

        # แสดงใน terminal (handle Windows cp874 encoding)
        out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        out.write(message + '\n\n')
        out.flush()

        if dry_run:
            self.stdout.write(self.style.WARNING('(dry-run — ไม่ได้ส่ง Line Notify)'))
            return

        # ส่ง Line Notify
        token = getattr(settings, 'LINENOTIFY_TOKEN', None)
        if not token:
            self.stdout.write(self.style.WARNING(
                '⚠️  ไม่มี LINENOTIFY_TOKEN — ข้ามการส่ง Line Notify\n'
                '   เพิ่มใน .env: LINENOTIFY_TOKEN=your_token'
            ))
            return

        try:
            resp = requests.post(
                'https://notify-api.line.me/api/notify',
                headers={'Authorization': f'Bearer {token}'},
                data={'message': message},
                timeout=10,
            )
            if resp.status_code == 200:
                self.stdout.write(self.style.SUCCESS('✅ ส่ง Line Notify สำเร็จ'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'❌ Line Notify error: {resp.status_code} — {resp.text}'
                ))
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'❌ ส่งไม่ได้: {e}'))
