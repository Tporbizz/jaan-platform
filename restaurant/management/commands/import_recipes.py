"""
นำเข้าสูตรอาหารจริงของร้าน (50 เมนู) จากไฟล์ recipes.csv
สร้าง/อัปเดต MenuItem + Recipe + RecipeItem และผูกเมนู↔สูตรให้อัตโนมัติ

โครงไฟล์: หมวด, ชื่อเมนู, ราคาขาย, วัตถุดิบ, ปริมาณต่อจาน, หน่วย, ราคาต่อหน่วย, ต้นทุน

  python manage.py import_recipes              # นำเข้า tenant แรก
  python manage.py import_recipes --dry-run

จับวัตถุดิบกับ Item ที่มีอยู่ด้วยชื่อ (normalize) ถ้าไม่เจอจะสร้างใหม่
รันซ้ำได้ — อัปเดตสูตรเดิม (idempotent)
"""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Tenant
from restaurant.models import Category, Item, MenuItem, Recipe, RecipeItem, Unit

DEFAULT_CSV = Path(__file__).resolve().parent.parent / 'data' / 'recipes.csv'

# หมวดในไฟล์ → MenuCategory ของระบบ
CATEGORY_MAP = {
    'brunch': 'single_dish',
    'thai fusion': 'single_dish',
    'pasta': 'pasta',
    'dessert': 'dessert',
    'beverage': 'soft_drink',
}


def _dec(v, default='0'):
    try:
        return Decimal(str(v).replace(',', '').strip() or default)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _norm(s):
    return ''.join(str(s or '').split()).lower()


class Command(BaseCommand):
    help = 'นำเข้าสูตรอาหาร (เมนู+ส่วนผสม) จาก recipes.csv'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=int)
        parser.add_argument('--file', type=str, default=str(DEFAULT_CSV))
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        path = Path(opts['file'])
        if not path.exists():
            raise CommandError(f'ไม่พบไฟล์: {path}')
        tenant = (Tenant.objects.filter(id=opts['tenant']).first() if opts.get('tenant')
                  else Tenant.objects.order_by('id').first())
        if not tenant:
            raise CommandError('ไม่พบ Tenant')

        dry = opts['dry_run']

        # อ่าน + จัดกลุ่มตามเมนู
        menus = {}
        with open(path, encoding='utf-8-sig') as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0 or len(row) < 6:
                    continue
                cat, name, price, ing, qty, unit = (row[0].strip(), row[1].strip(),
                                                    row[2], row[3].strip(), row[4], row[5].strip())
                if not name:
                    continue
                m = menus.setdefault(name, {'cat': cat, 'price': price, 'ings': []})
                if ing:
                    m['ings'].append((ing, qty, unit))

        if dry:
            total_ing = sum(len(v['ings']) for v in menus.values())
            self.stdout.write(self.style.SUCCESS(
                f'[DRY] จะนำเข้า {len(menus)} เมนู, {total_ing} ส่วนผสม'))
            return

        # cache
        items_by_norm = {_norm(it.name): it for it in Item.objects.filter(tenant=tenant)}
        units = {u.name: u for u in Unit.objects.filter(tenant=tenant)}
        default_unit = units.get('หน่วย') or Unit.objects.create(
            tenant=tenant, name='หน่วย', abbreviation='หน่วย')
        units['หน่วย'] = default_unit
        ing_cat, _ = Category.objects.get_or_create(tenant=tenant, name='วัตถุดิบนำเข้าสูตร')

        n_menu = n_recipe = n_ing = n_newitem = 0

        for name, data in menus.items():
            with transaction.atomic():
                menu_cat = CATEGORY_MAP.get(data['cat'].lower(), 'single_dish')
                menu = MenuItem.objects.filter(tenant=tenant, name=name).first()
                if not menu:
                    menu = MenuItem(tenant=tenant, name=name)
                menu.selling_price = _dec(data['price'])
                menu.menu_category = menu_cat
                menu.is_available = True

                recipe, _ = Recipe.objects.get_or_create(tenant=tenant, name=name)
                menu.recipe = recipe
                menu.save()
                n_menu += 1
                n_recipe += 1

                # สร้างส่วนผสมใหม่ทั้งหมด (idempotent)
                recipe.ingredients.all().delete()
                for ing_name, qty, unit_name in data['ings']:
                    item = items_by_norm.get(_norm(ing_name))
                    if not item:
                        u = units.get(unit_name) if unit_name else default_unit
                        if not u:
                            u = Unit.objects.create(tenant=tenant, name=unit_name, abbreviation=unit_name[:10])
                            units[unit_name] = u
                        item = Item.objects.create(
                            tenant=tenant, name=ing_name, category=ing_cat,
                            unit=u, cost_per_unit=Decimal('0'),
                        )
                        items_by_norm[_norm(ing_name)] = item
                        n_newitem += 1
                    u = units.get(unit_name) if unit_name else item.unit
                    if not u:
                        u = item.unit or default_unit
                    RecipeItem.objects.create(
                        recipe=recipe, item=item,
                        quantity=_dec(qty, '1'), unit=u,
                    )
                    n_ing += 1

        self.stdout.write(self.style.SUCCESS(
            f'[OK] เมนู {n_menu} | สูตร {n_recipe} | ส่วนผสม {n_ing} '
            f'| วัตถุดิบใหม่ {n_newitem}'))
