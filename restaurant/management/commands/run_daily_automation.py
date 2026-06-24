"""
รันงานอัตโนมัติประจำวันสำหรับทุกร้าน:
  1. สั่งซื้ออัตโนมัติ (ร่าง) สำหรับของต่ำกว่าขั้นต่ำ
  2. แจ้งเตือนของใกล้หมดอายุ
  3. แจ้งเตือนของใกล้หมดสต็อก
  4. ปิดยอด P&L เดือนปัจจุบัน

ใช้ได้กับ Render Cron:  python manage.py run_daily_automation
หรือเรียกผ่าน Celery beat (ดู jaan_platform/celery.py)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Tenant
from core.notify import notify
from restaurant.services import (
    auto_generate_reorder_pos, scan_expiring_lots, scan_low_stock,
)
from reports.services import rollup_monthly_pl


class Command(BaseCommand):
    help = 'รันงานอัตโนมัติประจำวัน (สั่งซื้อ/หมดอายุ/สต็อกต่ำ/P&L) ทุกร้าน'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, help='จำกัดเฉพาะ tenant id เดียว')
        parser.add_argument('--expiry-days', type=int, default=3, help='เตือนของหมดอายุภายใน N วัน')

    def handle(self, *args, **opts):
        tenants = Tenant.objects.filter(is_active=True)
        if opts.get('tenant'):
            tenants = tenants.filter(id=opts['tenant'])

        today = timezone.localdate()
        for tenant in tenants:
            self.stdout.write(self.style.HTTP_INFO(f"\n>> {tenant.name}"))
            self._run_for_tenant(tenant, today, opts['expiry_days'])

        self.stdout.write(self.style.SUCCESS('\n[OK] เสร็จสิ้นงานอัตโนมัติประจำวัน'))

    def _run_for_tenant(self, tenant, today, expiry_days):
        # 1. สั่งซื้ออัตโนมัติ
        pos = auto_generate_reorder_pos(tenant)
        if pos:
            names = ', '.join(p.po_number for p in pos)
            notify(
                tenant,
                title=f'สร้างใบสั่งซื้ออัตโนมัติ {len(pos)} ใบ',
                message=f'PO ร่างรออนุมัติ: {names}',
                level='warning', category='reorder', link='/procurement/po/',
            )
            self.stdout.write(f'  - สั่งซื้ออัตโนมัติ: {len(pos)} ใบ ({names})')
        else:
            self.stdout.write('  - สั่งซื้ออัตโนมัติ: ไม่มีรายการ')

        # 2. ของใกล้หมดอายุ
        expiring = scan_expiring_lots(tenant, days=expiry_days)
        if expiring:
            lines = ', '.join(f'{l.item.name} ({l.days_until_expiry()} วัน)' for l in expiring[:8])
            notify(
                tenant,
                title=f'ของใกล้หมดอายุ {len(expiring)} รายการ',
                message=lines, level='danger', category='expiry', link='/stock/',
            )
            self.stdout.write(f'  - ใกล้หมดอายุ: {len(expiring)} รายการ')
        else:
            self.stdout.write('  - ใกล้หมดอายุ: ไม่มี')

        # 3. สต็อกต่ำ
        low = scan_low_stock(tenant)
        if low:
            notify(
                tenant,
                title=f'สต็อกต่ำกว่าขั้นต่ำ {len(low)} รายการ',
                message=', '.join(i.name for i in low[:10]),
                level='warning', category='stock', link='/stock/',
            )
            self.stdout.write(f'  - สต็อกต่ำ: {len(low)} รายการ')

        # 4. ปิดยอด P&L เดือนปัจจุบัน
        pl = rollup_monthly_pl(tenant, today.month, today.year)
        self.stdout.write(
            f'  - P&L {today.month}/{today.year}: รายได้ ฿{pl.total_revenue:,.0f} '
            f'| FC {pl.food_cost_pct:.1f}% | กำไรสุทธิ ฿{pl.net_profit:,.0f}'
        )
