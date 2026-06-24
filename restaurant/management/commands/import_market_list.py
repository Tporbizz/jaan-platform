"""
นำเข้า Market List จริงของร้าน (วัตถุดิบ ~620 รายการ) จากไฟล์ CSV
สร้าง/อัปเดต Item พร้อม หมวดหมู่ (จาก Group), ผู้จำหน่าย, หน่วยสูตร, ต้นทุนต่อหน่วยสูตร

  python manage.py import_market_list                 # ใช้ไฟล์ใน repo, tenant แรก
  python manage.py import_market_list --tenant 1
  python manage.py import_market_list --file path.csv --dry-run

จับคู่ด้วย Item.code (ITEM NO. เช่น FF-0001) → รันซ้ำได้ ไม่สร้างซ้ำ (idempotent)
"""
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from accounts.models import Tenant
from restaurant.models import Category, Item, Supplier, Unit

# Group code → ชื่อหมวดหมู่ไทย
GROUP_LABELS = {
    'AS': 'บรรจุภัณฑ์/อุปกรณ์',
    'CL': 'ของใช้ทำความสะอาด',
    'FF': 'ของสด',
    'FZ': 'ของแช่แข็ง',
    'SS': 'เครื่องปรุง/ของแห้ง',
    'JJ': 'เบ็ดเตล็ด',
    'FB': 'เครื่องดื่ม',
}

DEFAULT_CSV = Path(__file__).resolve().parent.parent / 'data' / 'market_list.csv'


def _money(s):
    """' ฿ 1,090.00 ' -> Decimal('1090.00'); คืน 0 ถ้าแปลงไม่ได้"""
    if not s:
        return Decimal('0')
    cleaned = re.sub(r'[^\d.]', '', s.replace(',', ''))
    try:
        return Decimal(cleaned) if cleaned else Decimal('0')
    except InvalidOperation:
        return Decimal('0')


def _norm_unit(s):
    """normalize หน่วย: ตัด space, แก้ 'กรััม' -> 'กรัม'"""
    u = (s or '').strip().replace('กรััม', 'กรัม')
    return u or 'หน่วย'


class Command(BaseCommand):
    help = 'นำเข้า Market List จริงของร้าน (วัตถุดิบ) จาก CSV'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, help='tenant id (ดีฟอลต์ = tenant แรก)')
        parser.add_argument('--file', type=str, default=str(DEFAULT_CSV), help='พาธไฟล์ CSV')
        parser.add_argument('--dry-run', action='store_true', help='ทดลองโดยไม่บันทึก')

    def handle(self, *args, **opts):
        path = Path(opts['file'])
        if not path.exists():
            raise CommandError(f'ไม่พบไฟล์: {path}')

        tenant = (Tenant.objects.filter(id=opts['tenant']).first() if opts.get('tenant')
                  else Tenant.objects.order_by('id').first())
        if not tenant:
            raise CommandError('ไม่พบ Tenant — สร้างร้านก่อน')

        dry = opts['dry_run']
        self.stdout.write(self.style.HTTP_INFO(f'ร้าน: {tenant.name} | ไฟล์: {path.name}{" (DRY RUN)" if dry else ""}'))

        # cache เพื่อลด query
        cats = {c.name: c for c in Category.objects.filter(tenant=tenant)}
        units = {u.name: u for u in Unit.objects.filter(tenant=tenant)}
        sups = {s.name: s for s in Supplier.objects.filter(tenant=tenant)}

        created = updated = skipped = 0

        with open(path, encoding='utf-8-sig') as f:
            for row in csv.reader(f):
                if len(row) < 15:
                    continue
                code = row[1].strip()
                name = row[2].strip()
                if not name or code in ('ITEM NO.', ''):
                    continue

                group = row[3].strip() or 'JJ'
                supplier_name = row[5].strip()
                recipe_unit = _norm_unit(row[13])
                recipe_cost = _money(row[14])

                cat_label = GROUP_LABELS.get(group, group)
                cat = cats.get(cat_label)
                unit = units.get(recipe_unit)
                sup = sups.get(supplier_name) if supplier_name else None

                if not dry:
                    if not cat:
                        cat = Category.objects.create(tenant=tenant, name=cat_label)
                        cats[cat_label] = cat
                    if not unit:
                        unit = Unit.objects.create(tenant=tenant, name=recipe_unit, abbreviation=recipe_unit[:10])
                        units[recipe_unit] = unit
                    if supplier_name and not sup:
                        sup = Supplier.objects.create(tenant=tenant, name=supplier_name)
                        sups[supplier_name] = sup

                    item = Item.objects.filter(tenant=tenant, code=code).first() if code else None
                    if not item:
                        item = Item.objects.filter(tenant=tenant, name=name).first()
                    if item:
                        item.code = code or item.code
                        item.name = name
                        item.category = cat
                        item.unit = unit
                        item.cost_per_unit = recipe_cost
                        if sup:
                            item.default_supplier = sup
                        item.save()
                        updated += 1
                    else:
                        Item.objects.create(
                            tenant=tenant, code=code, name=name, category=cat,
                            unit=unit, cost_per_unit=recipe_cost, default_supplier=sup,
                        )
                        created += 1
                else:
                    skipped += 1

        if dry:
            self.stdout.write(self.style.SUCCESS(f'[DRY] จะนำเข้า ~{skipped} รายการ'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'[OK] สร้างใหม่ {created} | อัปเดต {updated} รายการ '
                f'| หมวด {len(cats)} | หน่วย {len(units)} | ผู้จำหน่าย {len(sups)}'
            ))
