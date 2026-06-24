"""
ผูกเมนูเข้ากับสูตรอาหารอัตโนมัติ โดยจับคู่จากชื่อ (normalize ช่องว่าง/ตัวพิมพ์)
ใช้หลัง seed หรือเมื่อสร้างสูตรชื่อตรงกับเมนู — ระบบตัดสต็อกจะทำงานทันที

  python manage.py link_menu_recipes            # ผูกจริง
  python manage.py link_menu_recipes --dry-run  # ดูก่อนว่าจะผูกคู่ไหน
"""
from django.core.management.base import BaseCommand

from accounts.models import Tenant
from restaurant.models import MenuItem, Recipe


def _norm(s):
    return ''.join((s or '').split()).lower()


class Command(BaseCommand):
    help = 'ผูกเมนูเข้ากับสูตรอาหารอัตโนมัติจากชื่อที่ตรงกัน'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int, help='จำกัดเฉพาะ tenant id')
        parser.add_argument('--dry-run', action='store_true', help='แสดงผลโดยไม่บันทึก')

    def handle(self, *args, **opts):
        tenants = Tenant.objects.all()
        if opts.get('tenant'):
            tenants = tenants.filter(id=opts['tenant'])

        total = 0
        for tenant in tenants:
            recipes = {_norm(r.name): r for r in Recipe.objects.filter(tenant=tenant)}
            menus = MenuItem.objects.filter(tenant=tenant, recipe__isnull=True)
            linked = 0
            for menu in menus:
                recipe = recipes.get(_norm(menu.name))
                if not recipe:
                    continue
                self.stdout.write(f'  {menu.name}  ->  สูตร {recipe.name}')
                if not opts['dry_run']:
                    menu.recipe = recipe
                    menu.save(update_fields=['recipe'])
                linked += 1
            total += linked
            self.stdout.write(self.style.HTTP_INFO(f'{tenant.name}: ผูก {linked} เมนู'))

        verb = 'จะผูก' if opts['dry_run'] else 'ผูกแล้ว'
        self.stdout.write(self.style.SUCCESS(f'\n[OK] {verb} {total} เมนูทั้งหมด'))
