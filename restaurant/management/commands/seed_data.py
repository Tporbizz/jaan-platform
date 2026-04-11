"""
Seed mock data สำหรับร้านอาหารไทยใต้ — สารข้าว Restaurant
วัตถุดิบ, เมนู, supplier, recipe ครบ
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import RestaurantBranch, Tenant, User
from restaurant.models import (
    Category, Item, KPITarget, LotBatch, MenuItem, POItem,
    PurchaseOrder, Recipe, RecipeItem, Subcategory, Supplier,
    Unit, WasteRecord,
)


class Command(BaseCommand):
    help = 'Seed mock data — ร้านอาหารไทยใต้ สารข้าว'

    def handle(self, *args, **options):
        self.stdout.write('🍽️  กำลังสร้าง mock data สำหรับสารข้าว Restaurant...\n')

        # --- Tenant & Branch ---
        tenant, _ = Tenant.objects.get_or_create(
            slug='sarkao',
            defaults={'name': 'สารข้าว Restaurant'},
        )
        branch, _ = RestaurantBranch.objects.get_or_create(
            tenant=tenant, name='สาขา Parima Hotel',
            defaults={'address': 'Parima Hotel, Trang', 'phone': '075-211-111'},
        )

        # --- Admin User ---
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@jaan.app',
                'first_name': 'Admin',
                'last_name': 'สารข้าว',
                'role': 'owner',
                'tenant': tenant,
                'restaurant_branch': branch,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin_user.set_password('jaan1234')
            admin_user.save()
            self.stdout.write('  ✅ สร้าง admin user (admin / jaan1234)')
        else:
            if not admin_user.tenant:
                admin_user.tenant = tenant
                admin_user.restaurant_branch = branch
                admin_user.role = 'owner'
                admin_user.save()
            self.stdout.write('  ℹ️  admin user มีอยู่แล้ว')

        # --- Staff Users ---
        for uname, fname, role in [
            ('somchai', 'สมชาย', 'manager'),
            ('nong', 'น้อง', 'staff'),
            ('view', 'วิว', 'staff'),
        ]:
            u, c = User.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname, 'role': role,
                    'tenant': tenant, 'restaurant_branch': branch,
                },
            )
            if c:
                u.set_password('jaan1234')
                u.save()

        # --- Units ---
        units = {}
        for name, abbr in [
            ('กิโลกรัม', 'kg'), ('กรัม', 'g'), ('ลิตร', 'L'),
            ('มิลลิลิตร', 'ml'), ('ขวด', 'btl'), ('ถุง', 'bag'),
            ('กล่อง', 'box'), ('ชิ้น', 'pc'), ('หัว', 'head'),
            ('ต้น', 'stalk'), ('ลูก', 'fruit'), ('แพ็ค', 'pack'),
        ]:
            units[abbr], _ = Unit.objects.get_or_create(
                tenant=tenant, abbreviation=abbr,
                defaults={'name': name},
            )

        # --- Categories ---
        cats = {}
        for name, order in [
            ('เนื้อสัตว์/อาหารทะเล', 1),
            ('ผักสด', 2),
            ('เครื่องปรุง/ซอส', 3),
            ('ข้าว/แป้ง/เส้น', 4),
            ('ผลไม้', 5),
            ('เครื่องดื่ม', 6),
            ('ของแห้ง', 7),
            ('นม/ไข่', 8),
        ]:
            cats[name], _ = Category.objects.get_or_create(
                tenant=tenant, name=name,
                defaults={'sort_order': order},
            )

        # --- Suppliers (ตรัง) ---
        suppliers = {}
        for sname, contact, phone in [
            ('ตลาดสดตรัง', 'พี่เจ', '089-111-1111'),
            ('ร้านปลาทะเลตรัง', 'พี่ต้น', '089-222-2222'),
            ('แม็คโคร ตรัง', 'Call Center', '1432'),
            ('ฟาร์มผักออร์แกนิค', 'พี่นก', '089-333-3333'),
            ('ร้านเครื่องดื่มตรัง', 'พี่บอย', '089-444-4444'),
        ]:
            suppliers[sname], _ = Supplier.objects.get_or_create(
                tenant=tenant, name=sname,
                defaults={'contact_person': contact, 'phone': phone},
            )

        # --- Items (วัตถุดิบ ร้านอาหารไทยใต้) ---
        today = timezone.now().date()
        items_data = [
            # (name, category, unit, supplier, stock, min, max, cost)
            ('กุ้งแชบ๊วย', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ร้านปลาทะเลตรัง', 8, 5, 20, 280),
            ('ปลากะพงแดง', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ร้านปลาทะเลตรัง', 5, 3, 15, 220),
            ('ปลาหมึกกล้วย', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ร้านปลาทะเลตรัง', 6, 3, 12, 180),
            ('ปูม้า', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ร้านปลาทะเลตรัง', 4, 2, 10, 350),
            ('หอยแมลงภู่', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ร้านปลาทะเลตรัง', 10, 5, 15, 80),
            ('หมูสามชั้น', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ตลาดสดตรัง', 7, 5, 15, 180),
            ('ไก่ทั้งตัว', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ตลาดสดตรัง', 10, 5, 20, 85),
            ('เนื้อแพะ', 'เนื้อสัตว์/อาหารทะเล', 'kg', 'ตลาดสดตรัง', 3, 2, 8, 320),

            ('สะตอ', 'ผักสด', 'pack', 'ตลาดสดตรัง', 15, 10, 30, 40),
            ('ใบเหลียง', 'ผักสด', 'pack', 'ฟาร์มผักออร์แกนิค', 12, 8, 20, 25),
            ('ขมิ้นสด', 'ผักสด', 'kg', 'ตลาดสดตรัง', 3, 2, 5, 60),
            ('ตะไคร้', 'ผักสด', 'stalk', 'ตลาดสดตรัง', 30, 20, 50, 3),
            ('ใบมะกรูด', 'ผักสด', 'pack', 'ตลาดสดตรัง', 10, 5, 15, 15),
            ('พริกขี้หนูสด', 'ผักสด', 'kg', 'ตลาดสดตรัง', 2, 1, 5, 120),
            ('ข่า', 'ผักสด', 'kg', 'ตลาดสดตรัง', 2, 1, 4, 80),
            ('ผักกูดสด', 'ผักสด', 'pack', 'ฟาร์มผักออร์แกนิค', 8, 5, 15, 30),
            ('ถั่วงอก', 'ผักสด', 'kg', 'ตลาดสดตรัง', 3, 2, 5, 25),
            ('ผักบุ้ง', 'ผักสด', 'pack', 'ฟาร์มผักออร์แกนิค', 10, 5, 15, 15),

            ('กะปิเกาะยอ', 'เครื่องปรุง/ซอส', 'kg', 'ตลาดสดตรัง', 3, 2, 5, 180),
            ('น้ำปลา', 'เครื่องปรุง/ซอส', 'btl', 'แม็คโคร ตรัง', 5, 3, 8, 45),
            ('น้ำตาลปี๊บ', 'เครื่องปรุง/ซอส', 'kg', 'ตลาดสดตรัง', 4, 3, 8, 70),
            ('พริกแกงส้ม', 'เครื่องปรุง/ซอส', 'kg', 'ตลาดสดตรัง', 2, 1, 4, 200),
            ('พริกแกงเหลือง', 'เครื่องปรุง/ซอส', 'kg', 'ตลาดสดตรัง', 2, 1, 4, 220),
            ('น้ำมะขามเปียก', 'เครื่องปรุง/ซอส', 'btl', 'แม็คโคร ตรัง', 3, 2, 5, 55),
            ('ซอสหอยนางรม', 'เครื่องปรุง/ซอส', 'btl', 'แม็คโคร ตรัง', 4, 2, 6, 60),

            ('ข้าวสารหอมมะลิ', 'ข้าว/แป้ง/เส้น', 'kg', 'แม็คโคร ตรัง', 50, 30, 100, 38),
            ('ขนมจีนสด', 'ข้าว/แป้ง/เส้น', 'kg', 'ตลาดสดตรัง', 5, 3, 10, 30),
            ('เส้นหมี่', 'ข้าว/แป้ง/เส้น', 'pack', 'แม็คโคร ตรัง', 10, 5, 15, 25),

            ('มะพร้าว', 'ผลไม้', 'fruit', 'ตลาดสดตรัง', 20, 10, 30, 15),
            ('มะนาว', 'ผลไม้', 'fruit', 'ตลาดสดตรัง', 30, 20, 50, 3),

            ('น้ำดื่ม', 'เครื่องดื่ม', 'box', 'ร้านเครื่องดื่มตรัง', 10, 5, 20, 85),
            ('โค้ก/เป็ปซี่', 'เครื่องดื่ม', 'box', 'ร้านเครื่องดื่มตรัง', 5, 3, 10, 280),
            ('เบียร์สิงห์', 'เครื่องดื่ม', 'box', 'ร้านเครื่องดื่มตรัง', 3, 2, 8, 680),
            ('ชาร้อน/เย็น', 'เครื่องดื่ม', 'pack', 'แม็คโคร ตรัง', 8, 5, 12, 120),

            ('ไข่ไก่', 'นม/ไข่', 'pack', 'แม็คโคร ตรัง', 5, 3, 10, 110),
            ('กะทิกล่อง', 'นม/ไข่', 'box', 'แม็คโคร ตรัง', 6, 4, 10, 350),
        ]

        items = {}
        for name, cat_name, unit_key, sup_name, stock, minv, maxv, cost in items_data:
            item, _ = Item.objects.get_or_create(
                tenant=tenant, name=name,
                defaults={
                    'category': cats[cat_name],
                    'unit': units[unit_key],
                    'default_supplier': suppliers[sup_name],
                    'current_stock': Decimal(str(stock)),
                    'min_stock': Decimal(str(minv)),
                    'max_stock': Decimal(str(maxv)),
                    'cost_per_unit': Decimal(str(cost)),
                },
            )
            items[name] = item

        self.stdout.write(f'  ✅ สร้างวัตถุดิบ {len(items_data)} รายการ')

        # --- LotBatch (บาง items มี expiry) ---
        lot_data = [
            ('กุ้งแชบ๊วย', 2, 280, -1),    # expired yesterday
            ('กุ้งแชบ๊วย', 6, 280, 2),      # expires in 2 days
            ('ปลากะพงแดง', 5, 220, 3),      # expires in 3 days
            ('ปลาหมึกกล้วย', 6, 180, 5),
            ('หมูสามชั้น', 7, 180, 4),
            ('ไก่ทั้งตัว', 10, 85, 6),
            ('ใบเหลียง', 12, 25, 1),        # expires tomorrow!
            ('สะตอ', 15, 40, 5),
            ('กะทิกล่อง', 6, 350, 90),
            ('ไข่ไก่', 5, 110, 14),
        ]
        for item_name, qty, cost, days in lot_data:
            LotBatch.objects.get_or_create(
                tenant=tenant, item=items[item_name],
                lot_number=f"L{timezone.now().strftime('%m%d')}-{item_name[:3]}",
                defaults={
                    'quantity': Decimal(str(qty)),
                    'cost_per_unit': Decimal(str(cost)),
                    'received_date': today - timedelta(days=3),
                    'expiry_date': today + timedelta(days=days),
                    'supplier': items[item_name].default_supplier,
                },
            )

        self.stdout.write(f'  ✅ สร้าง LotBatch {len(lot_data)} รายการ')

        # --- Recipes (เมนูไทยใต้) ---
        recipes_data = {
            'แกงส้มกุ้ง': [
                ('กุ้งแชบ๊วย', Decimal('0.25'), 'kg'),
                ('พริกแกงส้ม', Decimal('0.05'), 'kg'),
                ('น้ำปลา', Decimal('0.03'), 'btl'),
                ('น้ำตาลปี๊บ', Decimal('0.02'), 'kg'),
                ('น้ำมะขามเปียก', Decimal('0.02'), 'btl'),
            ],
            'แกงเหลืองปลากะพง': [
                ('ปลากะพงแดง', Decimal('0.3'), 'kg'),
                ('พริกแกงเหลือง', Decimal('0.05'), 'kg'),
                ('ขมิ้นสด', Decimal('0.02'), 'kg'),
                ('น้ำปลา', Decimal('0.02'), 'btl'),
            ],
            'ผัดสะตอกุ้ง': [
                ('กุ้งแชบ๊วย', Decimal('0.2'), 'kg'),
                ('สะตอ', Decimal('1'), 'pack'),
                ('กะปิเกาะยอ', Decimal('0.02'), 'kg'),
                ('พริกขี้หนูสด', Decimal('0.02'), 'kg'),
                ('น้ำปลา', Decimal('0.01'), 'btl'),
            ],
            'ปลาหมึกผัดขมิ้น': [
                ('ปลาหมึกกล้วย', Decimal('0.25'), 'kg'),
                ('ขมิ้นสด', Decimal('0.03'), 'kg'),
                ('พริกขี้หนูสด', Decimal('0.01'), 'kg'),
                ('ซอสหอยนางรม', Decimal('0.02'), 'btl'),
            ],
            'ผัดผักกูดไฟแดง': [
                ('ผักกูดสด', Decimal('1'), 'pack'),
                ('กุ้งแชบ๊วย', Decimal('0.1'), 'kg'),
                ('กะปิเกาะยอ', Decimal('0.01'), 'kg'),
                ('น้ำปลา', Decimal('0.01'), 'btl'),
            ],
            'แกงพะแนงเนื้อแพะ': [
                ('เนื้อแพะ', Decimal('0.3'), 'kg'),
                ('กะทิกล่อง', Decimal('0.1'), 'box'),
                ('พริกแกงเหลือง', Decimal('0.04'), 'kg'),
                ('น้ำปลา', Decimal('0.02'), 'btl'),
                ('น้ำตาลปี๊บ', Decimal('0.02'), 'kg'),
            ],
            'ไก่ทอดหาดใหญ่': [
                ('ไก่ทั้งตัว', Decimal('0.4'), 'kg'),
                ('ขมิ้นสด', Decimal('0.03'), 'kg'),
                ('ไข่ไก่', Decimal('0.1'), 'pack'),
            ],
            'ข้าวยำ': [
                ('ข้าวสารหอมมะลิ', Decimal('0.2'), 'kg'),
                ('กะปิเกาะยอ', Decimal('0.02'), 'kg'),
                ('มะนาว', Decimal('2'), 'fruit'),
                ('ใบเหลียง', Decimal('0.5'), 'pack'),
            ],
            'ปูผัดผงกะหรี่': [
                ('ปูม้า', Decimal('0.3'), 'kg'),
                ('ไข่ไก่', Decimal('0.1'), 'pack'),
                ('ซอสหอยนางรม', Decimal('0.02'), 'btl'),
            ],
            'ขนมจีนน้ำยาปู': [
                ('ขนมจีนสด', Decimal('0.3'), 'kg'),
                ('ปูม้า', Decimal('0.15'), 'kg'),
                ('กะทิกล่อง', Decimal('0.1'), 'box'),
                ('พริกแกงเหลือง', Decimal('0.03'), 'kg'),
            ],
        }

        for rname, ingredients in recipes_data.items():
            recipe, _ = Recipe.objects.get_or_create(
                tenant=tenant, name=rname,
                defaults={'portions': 1},
            )
            for item_name, qty, unit_key in ingredients:
                RecipeItem.objects.get_or_create(
                    recipe=recipe, item=items[item_name],
                    defaults={'quantity': qty, 'unit': units[unit_key]},
                )

        self.stdout.write(f'  ✅ สร้าง Recipe {len(recipes_data)} เมนู')

        # --- Menu Items ---
        menu_data = [
            # (name, name_en, category, recipe_name, price)
            ('แกงส้มกุ้ง', 'Sour Curry with Shrimp', 'soup', 'แกงส้มกุ้ง', 180),
            ('แกงเหลืองปลากะพง', 'Southern Yellow Curry with Snapper', 'soup', 'แกงเหลืองปลากะพง', 220),
            ('แกงพะแนงเนื้อแพะ', 'Panang Curry with Goat', 'soup', 'แกงพะแนงเนื้อแพะ', 280),
            ('ขนมจีนน้ำยาปู', 'Rice Noodles with Crab Curry', 'soup', 'ขนมจีนน้ำยาปู', 150),
            ('ผัดสะตอกุ้ง', 'Stir-fried Sataw with Shrimp', 'stir_fry', 'ผัดสะตอกุ้ง', 200),
            ('ปลาหมึกผัดขมิ้น', 'Squid Stir-fried with Turmeric', 'stir_fry', 'ปลาหมึกผัดขมิ้น', 180),
            ('ผัดผักกูดไฟแดง', 'Stir-fried Fiddlehead Fern', 'stir_fry', 'ผัดผักกูดไฟแดง', 120),
            ('ปูผัดผงกะหรี่', 'Crab in Curry Powder', 'stir_fry', 'ปูผัดผงกะหรี่', 350),
            ('ไก่ทอดหาดใหญ่', 'Hat Yai Fried Chicken', 'deep_fry', 'ไก่ทอดหาดใหญ่', 150),
            ('ข้าวยำ', 'Southern Rice Salad', 'salad', 'ข้าวยำ', 80),
            ('ข้าวสวย', 'Steamed Rice', 'main', None, 20),
            ('น้ำเปล่า', 'Water', 'beverage', None, 20),
            ('โค้ก/เป็ปซี่', 'Coke/Pepsi', 'beverage', None, 35),
            ('ชาเย็น', 'Thai Iced Tea', 'beverage', None, 45),
            ('เบียร์สิงห์', 'Singha Beer', 'beverage', None, 100),
        ]

        recipes_db = {r.name: r for r in Recipe.objects.filter(tenant=tenant)}
        for mname, en, mcat, rname, price in menu_data:
            MenuItem.objects.get_or_create(
                tenant=tenant, name=mname,
                defaults={
                    'name_en': en,
                    'menu_category': mcat,
                    'recipe': recipes_db.get(rname),
                    'selling_price': Decimal(str(price)),
                },
            )

        self.stdout.write(f'  ✅ สร้างเมนู {len(menu_data)} รายการ')

        # --- Waste Records ---
        waste_data = [
            ('กุ้งแชบ๊วย', Decimal('0.5'), 'expired', -2),
            ('ใบเหลียง', Decimal('2'), 'spoiled', -1),
            ('ปลากะพงแดง', Decimal('0.3'), 'over_prep', 0),
        ]
        for item_name, qty, reason, days in waste_data:
            WasteRecord.objects.get_or_create(
                tenant=tenant, item=items[item_name],
                waste_date=today + timedelta(days=days),
                defaults={
                    'quantity': qty,
                    'unit': items[item_name].unit,
                    'reason': reason,
                    'recorded_by': admin_user,
                },
            )

        self.stdout.write('  ✅ สร้าง WasteRecord 3 รายการ')

        # --- KPI Target ---
        KPITarget.objects.get_or_create(
            tenant=tenant, month=today.month, year=today.year,
            defaults={
                'food_cost_target_pct': Decimal('33'),
                'labour_cost_target_pct': Decimal('30'),
                'revenue_target': Decimal('300000'),
                'waste_budget': Decimal('5000'),
            },
        )

        # --- Purchase Orders ---
        po, created = PurchaseOrder.objects.get_or_create(
            tenant=tenant, po_number='001',
            defaults={
                'supplier': suppliers['ร้านปลาทะเลตรัง'],
                'status': 'sent',
                'order_date': today,
                'expected_date': today + timedelta(days=1),
                'created_by': admin_user,
            },
        )
        if created:
            for iname, qty, price in [
                ('กุ้งแชบ๊วย', 10, 280),
                ('ปลากะพงแดง', 5, 220),
                ('ปลาหมึกกล้วย', 5, 180),
            ]:
                POItem.objects.create(
                    purchase_order=po, item=items[iname],
                    quantity=qty, unit_price=price,
                )

        self.stdout.write('  ✅ สร้าง PO 1 ใบ')

        # =====================================================================
        # POS — Tables + Upsell Rules
        # =====================================================================
        from pos.models import MenuUpsellRule, Table

        tables_data = [
            ('1', 'ริมหน้าต่าง', 2, 'ในร้าน', 0, 0),
            ('2', '', 4, 'ในร้าน', 1, 0),
            ('3', '', 4, 'ในร้าน', 2, 0),
            ('4', 'มุมเงียบ', 2, 'ในร้าน', 3, 0),
            ('5', 'ครอบครัว', 6, 'ในร้าน', 0, 1),
            ('6', '', 4, 'ในร้าน', 1, 1),
            ('7', 'ริมน้ำ A', 4, 'ริมน้ำ', 0, 2),
            ('8', 'ริมน้ำ B', 4, 'ริมน้ำ', 1, 2),
            ('9', 'ริมน้ำ C', 6, 'ริมน้ำ', 2, 2),
            ('VIP', 'ห้อง VIP', 10, 'VIP', 0, 3),
        ]
        for num, name, cap, zone, gx, gy in tables_data:
            Table.objects.get_or_create(
                tenant=tenant, number=num,
                defaults={'name': name, 'capacity': cap, 'zone': zone,
                          'grid_x': gx, 'grid_y': gy},
            )
        self.stdout.write(f'  ✅ สร้างโต๊ะ {len(tables_data)} โต๊ะ')

        # Upsell rules
        menu_db = {m.name: m for m in MenuItem.objects.filter(tenant=tenant)}
        upsell_data = [
            ('couple', 'แกงพะแนงเนื้อแพะ', 'เมนูพิเศษสำหรับคู่', 10),
            ('couple', 'เบียร์สิงห์', 'คู่กับอาหารเผ็ด', 8),
            ('couple', 'ชาเย็น', 'ดื่มหลังมื้อ', 5),
            ('has_children', 'ไก่ทอดหาดใหญ่', 'เด็กๆ ชอบ', 10),
            ('has_children', 'โค้ก/เป็ปซี่', 'เครื่องดื่มสำหรับเด็ก', 8),
            ('has_children', 'ข้าวสวย', 'ข้าวเพิ่มสำหรับเด็ก', 5),
            ('has_senior', 'แกงส้มกุ้ง', 'น้ำแกงอ่อนโยน', 10),
            ('has_senior', 'แกงเหลืองปลากะพง', 'ปลานุ่มย่อยง่าย', 8),
            ('group', 'ปูผัดผงกะหรี่', 'เมนูแชร์กลุ่ม', 10),
            ('group', 'เบียร์สิงห์', 'จัดเบียร์ให้กลุ่ม', 9),
            ('group', 'ผัดสะตอกุ้ง', 'จานแชร์ยอดนิยม', 7),
            ('men_only', 'เบียร์สิงห์', 'เบียร์เย็นๆ', 10),
            ('men_only', 'ผัดสะตอกุ้ง', 'จานเผ็ดจัดจ้าน', 8),
            ('default', 'แกงส้มกุ้ง', 'เมนูแนะนำ Best Seller', 10),
            ('default', 'ข้าวยำ', 'อาหารใต้แท้ๆ', 8),
            ('default', 'ชาเย็น', 'เครื่องดื่มยอดนิยม', 5),
        ]
        for ptype, menu_name, reason, priority in upsell_data:
            mi = menu_db.get(menu_name)
            if mi:
                MenuUpsellRule.objects.get_or_create(
                    tenant=tenant, profile_type=ptype, menu_item=mi,
                    defaults={'reason': reason, 'priority': priority},
                )
        self.stdout.write(f'  ✅ สร้าง Upsell Rules {len(upsell_data)} rules\n')

        self.stdout.write(self.style.SUCCESS(
            '🎉 Mock data พร้อมใช้งาน!\n'
            '   Login: admin / jaan1234\n'
            '   Staff: somchai, nong, view / jaan1234'
        ))
