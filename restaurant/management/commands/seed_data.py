"""
Seed mock data สำหรับร้านอาหารไทยใต้ — สารข้าว Restaurant
วัตถุดิบ, เมนู, supplier, recipe, POS orders, events, hotel, HR, reports, AC/IoT
"""
import datetime
import random
import uuid
from datetime import time, timedelta
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
    help = 'Seed mock data — ร้านอาหารไทยใต้ สารข้าว (ทุก Phase)'

    def handle(self, *args, **options):
        import io, sys
        self.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        self.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        self.stdout.write('🍽️  กำลังสร้าง mock data สำหรับสารข้าว Restaurant...\n')
        today = timezone.now().date()

        # =================================================================
        # Tenant & Branch & Users
        # =================================================================
        tenant, _ = Tenant.objects.get_or_create(
            slug='sarkao',
            defaults={'name': 'สารข้าว Restaurant'},
        )
        branch, _ = RestaurantBranch.objects.get_or_create(
            tenant=tenant, name='สาขา Parima Hotel',
            defaults={'address': 'Parima Hotel, Trang', 'phone': '075-211-111'},
        )

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

        staff_users = {}
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
            staff_users[uname] = u

        # =================================================================
        # Units
        # =================================================================
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

        # =================================================================
        # Categories
        # =================================================================
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

        # =================================================================
        # Suppliers (ตรัง)
        # =================================================================
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

        # =================================================================
        # Items (วัตถุดิบ ร้านอาหารไทยใต้)
        # =================================================================
        items_data = [
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

        # =================================================================
        # LotBatch
        # =================================================================
        lot_data = [
            ('กุ้งแชบ๊วย', 2, 280, -1),
            ('กุ้งแชบ๊วย', 6, 280, 2),
            ('ปลากะพงแดง', 5, 220, 3),
            ('ปลาหมึกกล้วย', 6, 180, 5),
            ('หมูสามชั้น', 7, 180, 4),
            ('ไก่ทั้งตัว', 10, 85, 6),
            ('ใบเหลียง', 12, 25, 1),
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

        # =================================================================
        # Recipes (เมนูไทยใต้)
        # =================================================================
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

        # =================================================================
        # Menu Items
        # =================================================================
        menu_data = [
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
        menu_db = {}
        for mname, en, mcat, rname, price in menu_data:
            mi, _ = MenuItem.objects.get_or_create(
                tenant=tenant, name=mname,
                defaults={
                    'name_en': en,
                    'menu_category': mcat,
                    'recipe': recipes_db.get(rname),
                    'selling_price': Decimal(str(price)),
                },
            )
            menu_db[mname] = mi
        self.stdout.write(f'  ✅ สร้างเมนู {len(menu_data)} รายการ')

        # =================================================================
        # Waste Records
        # =================================================================
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

        # =================================================================
        # KPI Target
        # =================================================================
        KPITarget.objects.get_or_create(
            tenant=tenant, month=today.month, year=today.year,
            defaults={
                'food_cost_target_pct': Decimal('33'),
                'labour_cost_target_pct': Decimal('30'),
                'revenue_target': Decimal('300000'),
                'waste_budget': Decimal('5000'),
            },
        )

        # =================================================================
        # Purchase Orders
        # =================================================================
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

        # =================================================================
        # POS — Tables + Upsell Rules
        # =================================================================
        from pos.models import (
            KitchenTicket, KitchenTicketItem, MenuUpsellRule,
            Order, OrderItem, Table, Transaction,
        )

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
        table_objs = {}
        for num, name, cap, zone, gx, gy in tables_data:
            t, _ = Table.objects.get_or_create(
                tenant=tenant, number=num,
                defaults={'name': name, 'capacity': cap, 'zone': zone,
                          'grid_x': gx, 'grid_y': gy},
            )
            table_objs[num] = t
        self.stdout.write(f'  ✅ สร้างโต๊ะ {len(tables_data)} โต๊ะ')

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
        self.stdout.write(f'  ✅ สร้าง Upsell Rules {len(upsell_data)} rules')

        # =================================================================
        # POS — Sample Orders (7 วันย้อนหลัง)
        # =================================================================
        order_count = 0
        popular_menus = ['แกงส้มกุ้ง', 'ผัดสะตอกุ้ง', 'ไก่ทอดหาดใหญ่',
                         'แกงเหลืองปลากะพง', 'ข้าวยำ', 'ปลาหมึกผัดขมิ้น',
                         'ข้าวสวย', 'ชาเย็น', 'น้ำเปล่า', 'เบียร์สิงห์']
        payment_methods = ['cash', 'promptpay', 'card', 'cash', 'promptpay']

        for day_offset in range(7):
            d = today - timedelta(days=day_offset)
            num_orders = random.randint(8, 15)
            for i in range(num_orders):
                table_key = random.choice(list(table_objs.keys()))
                order_num = f"{d.strftime('%y%m%d')}-{i+1:02d}"

                if Order.objects.filter(tenant=tenant, order_number=order_num).exists():
                    continue

                guest = random.randint(1, 6)
                men = random.randint(0, guest)
                women = guest - men
                children = random.randint(0, 1) if guest >= 3 else 0

                order = Order.objects.create(
                    tenant=tenant,
                    table=table_objs[table_key],
                    order_number=order_num,
                    status='paid',
                    guest_count=guest,
                    men_count=men,
                    women_count=women,
                    children_count=children,
                    created_by=admin_user,
                )
                # Force opened_at to correct date
                Order.objects.filter(id=order.id).update(
                    opened_at=timezone.make_aware(
                        datetime.datetime.combine(d, time(hour=random.randint(11, 20), minute=random.randint(0, 59)))
                    ),
                    closed_at=timezone.make_aware(
                        datetime.datetime.combine(d, time(hour=random.randint(12, 21), minute=random.randint(0, 59)))
                    ),
                )

                # Add items
                subtotal = Decimal('0')
                num_items = random.randint(2, 5)
                chosen_menus = random.sample(popular_menus, min(num_items, len(popular_menus)))
                for mname in chosen_menus:
                    mi = menu_db.get(mname)
                    if not mi:
                        continue
                    qty = 1 if mname != 'ข้าวสวย' else random.randint(1, guest)
                    OrderItem.objects.create(
                        order=order,
                        menu_item=mi,
                        quantity=qty,
                        unit_price=mi.selling_price,
                        status='served',
                    )
                    subtotal += mi.selling_price * qty

                order.subtotal = subtotal
                order.total = subtotal
                order.save(update_fields=['subtotal', 'total'])

                Transaction.objects.create(
                    tenant=tenant,
                    order=order,
                    payment_method=random.choice(payment_methods),
                    amount=subtotal,
                    received=subtotal,
                    processed_by=admin_user,
                )
                order_count += 1

        self.stdout.write(f'  ✅ สร้าง POS Orders {order_count} ออเดอร์')

        # =================================================================
        # Phase 4 — Events
        # =================================================================
        from events.models import EventOrder, EventOrderItem, EventSession

        # งานแต่ง — closed
        menu_snapshot = [
            {'id': 1, 'name': 'แกงส้มกุ้ง', 'name_en': 'Sour Curry', 'price': 180},
            {'id': 2, 'name': 'ผัดสะตอกุ้ง', 'name_en': 'Sataw Shrimp', 'price': 200},
            {'id': 3, 'name': 'ไก่ทอดหาดใหญ่', 'name_en': 'Hat Yai Chicken', 'price': 150},
            {'id': 4, 'name': 'ข้าวยำ', 'name_en': 'Rice Salad', 'price': 80},
            {'id': 5, 'name': 'ขนมจีนน้ำยาปู', 'name_en': 'Noodle Crab', 'price': 150},
            {'id': 6, 'name': 'ข้าวสวย', 'name_en': 'Rice', 'price': 20},
            {'id': 7, 'name': 'น้ำเปล่า', 'name_en': 'Water', 'price': 20},
            {'id': 8, 'name': 'ชาเย็น', 'name_en': 'Iced Tea', 'price': 45},
        ]

        ev1, ev1_created = EventSession.objects.get_or_create(
            tenant=tenant, name='งานแต่ง คุณสมศักดิ์-คุณนิดา',
            defaults={
                'date': today - timedelta(days=5),
                'location': 'ลานริมทะเล Parima Hotel',
                'status': 'closed',
                'menu_snapshot': menu_snapshot,
                'total_revenue': Decimal('12480'),
                'total_orders': 24,
                'notes': 'งานแต่ง 80 คน — บุฟเฟ่ต์อาหารใต้',
                'created_by': admin_user,
            },
        )
        if ev1_created:
            for i in range(1, 25):
                eo = EventOrder.objects.create(
                    session=ev1,
                    order_number=f"EV1-{i:03d}",
                    status='paid',
                    payment_method='promptpay',
                )
                eo_total = Decimal('0')
                for _ in range(random.randint(2, 4)):
                    snap = random.choice(menu_snapshot)
                    qty = random.randint(1, 2)
                    EventOrderItem.objects.create(
                        order=eo,
                        menu_item_name=snap['name'],
                        menu_item_id=snap['id'],
                        quantity=qty,
                        unit_price=Decimal(str(snap['price'])),
                    )
                    eo_total += Decimal(str(snap['price'])) * qty
                eo.subtotal = eo_total
                eo.total = eo_total
                eo.save(update_fields=['subtotal', 'total'])

        # เลี้ยงรุ่น — active
        ev2, ev2_created = EventSession.objects.get_or_create(
            tenant=tenant, name='เลี้ยงรุ่น ม.6/45 วิเชียรมาตุ',
            defaults={
                'date': today + timedelta(days=2),
                'location': 'ห้อง VIP สารข้าว',
                'status': 'active',
                'menu_snapshot': menu_snapshot,
                'notes': 'เลี้ยงรุ่น 30 คน — set menu',
                'created_by': admin_user,
            },
        )
        if ev2_created:
            for i in range(1, 8):
                eo = EventOrder.objects.create(
                    session=ev2,
                    order_number=f"EV2-{i:03d}",
                    status='paid' if i <= 5 else 'pending',
                    payment_method='promptpay' if i <= 5 else '',
                )
                eo_total = Decimal('0')
                for _ in range(random.randint(2, 3)):
                    snap = random.choice(menu_snapshot)
                    qty = random.randint(1, 2)
                    EventOrderItem.objects.create(
                        order=eo,
                        menu_item_name=snap['name'],
                        menu_item_id=snap['id'],
                        quantity=qty,
                        unit_price=Decimal(str(snap['price'])),
                    )
                    eo_total += Decimal(str(snap['price'])) * qty
                eo.subtotal = eo_total
                eo.total = eo_total
                eo.save(update_fields=['subtotal', 'total'])
            ev2.recalculate_totals()

        # งานสัมมนา — draft (อนาคต)
        EventSession.objects.get_or_create(
            tenant=tenant, name='สัมมนา ท่องเที่ยวตรัง 2026',
            defaults={
                'date': today + timedelta(days=14),
                'location': 'ห้องประชุม Parima Hotel',
                'status': 'draft',
                'menu_snapshot': menu_snapshot[:5],
                'notes': 'คาดการณ์ 50 คน — coffee break + lunch',
                'created_by': admin_user,
            },
        )
        self.stdout.write('  ✅ สร้าง Events 3 งาน + orders')

        # =================================================================
        # Phase 6 — Hotel Integration
        # =================================================================
        from hotel_integration.models import BFSettlement, GuestList, HotelConfig, RoomCharge

        HotelConfig.objects.get_or_create(
            tenant=tenant,
            defaults={
                'pms_type': 'ads',
                'sync_method': 'csv',
                'is_active': True,
            },
        )

        guest_data = [
            ('201', 'Mr. Tanaka Hiroshi', today + timedelta(days=3), 'BB', True, 0),
            ('202', 'คุณวิภา จันทร์แก้ว', today + timedelta(days=1), 'BB', True, 0),
            ('301', 'Mr. David Smith', today + timedelta(days=5), 'HB', True, 2000),
            ('302', 'คุณสุชาติ-คุณนภา', today + timedelta(days=2), 'FB', True, 5000),
            ('303', 'Ms. Lisa Chen', today + timedelta(days=4), 'RO', False, 0),
            ('401', 'คุณประพันธ์ ศรีตรัง', today + timedelta(days=1), 'BB', True, 0),
            ('402', 'Mr. & Mrs. Johnson', today + timedelta(days=6), 'HB', True, 3000),
            ('501', 'คุณธีรศักดิ์ รักษ์ทะเล', today + timedelta(days=3), 'BB', True, 0),
            ('VIP1', 'คุณหมอสมบัติ วงศ์ตรัง', today + timedelta(days=2), 'FB', True, 10000),
        ]
        for room, name, checkout, pkg, bf, balance in guest_data:
            GuestList.objects.get_or_create(
                tenant=tenant, room_number=room, import_date=today,
                defaults={
                    'guest_name': name,
                    'checkout_date': checkout,
                    'package_type': pkg,
                    'bf_included': bf,
                    'fb_balance': Decimal(str(balance)),
                },
            )
        self.stdout.write(f'  ✅ สร้าง Guest List {len(guest_data)} ห้อง')

        # Room Charges
        charge_data = [
            ('301', 'Mr. David Smith', 850, 'posted'),
            ('302', 'คุณสุชาติ', 1280, 'posted'),
            ('VIP1', 'คุณหมอสมบัติ', 2350, 'posted'),
            ('402', 'Mr. Johnson', 680, 'pending'),
            ('201', 'Mr. Tanaka', 450, 'pending'),
        ]
        for room, name, amount, status in charge_data:
            RoomCharge.objects.get_or_create(
                tenant=tenant, room_number=room, guest_name=name,
                amount=Decimal(str(amount)),
                defaults={'status': status, 'posted_by': admin_user},
            )
        self.stdout.write('  ✅ สร้าง Room Charges 5 รายการ')

        # BF Settlements — 7 วันย้อนหลัง
        for d_offset in range(7):
            d = today - timedelta(days=d_offset)
            bb = random.randint(8, 18)
            hb = random.randint(2, 5)
            fb = random.randint(1, 3)
            walkin = random.randint(2, 8)
            total = bb + hb + fb + walkin
            amount = bb * 250 + hb * 250 + walkin * 350
            BFSettlement.objects.get_or_create(
                tenant=tenant, date=d,
                defaults={
                    'total_covers': total,
                    'bb_covers': bb,
                    'hb_covers': hb,
                    'fb_covers': fb,
                    'walkin_covers': walkin,
                    'total_amount': Decimal(str(amount)),
                },
            )
        self.stdout.write('  ✅ สร้าง BF Settlement 7 วัน')

        # =================================================================
        # Phase 7 — HR + Employees + Shifts + Attendance + Payroll
        # =================================================================
        from hr.models import Attendance, Employee, PayrollRecord, ShiftSchedule

        employees_data = [
            ('เอก', 'ประสิทธิ์', 'เชฟเอก', 'chef', '089-555-0001', 25000, 0, 200),
            ('กุ้ง', 'ทะเลงาม', 'พี่กุ้ง', 'sous_chef', '089-555-0002', 18000, 0, 150),
            ('แนน', 'รักษ์ครัว', 'น้องแนน', 'cook', '089-555-0003', 15000, 0, 120),
            ('สมชาย', 'ใจดี', 'ชาย', 'server', '089-555-0004', 12000, 60, 90),
            ('มิ้นท์', 'สุขใส', 'มิ้นท์', 'server', '089-555-0005', 11000, 55, 83),
            ('แอ๋ม', 'บัญชีดี', 'พี่แอ๋ม', 'cashier', '089-555-0006', 14000, 0, 100),
            ('เบิร์ด', 'สะอาดจัง', 'น้องเบิร์ด', 'cleaner', '089-555-0007', 10000, 50, 75),
        ]
        emp_objs = {}
        for fname, lname, nick, pos, phone, salary, hourly, ot_rate in employees_data:
            emp, _ = Employee.objects.get_or_create(
                tenant=tenant, first_name=fname, last_name=lname,
                defaults={
                    'nickname': nick,
                    'position': pos,
                    'phone': phone,
                    'base_salary': Decimal(str(salary)),
                    'hourly_rate': Decimal(str(hourly)),
                    'ot_rate': Decimal(str(ot_rate)),
                    'start_date': today - timedelta(days=random.randint(90, 730)),
                },
            )
            emp_objs[nick] = emp
        self.stdout.write(f'  ✅ สร้างพนักงาน {len(employees_data)} คน')

        # Shifts — สัปดาห์นี้
        shift_patterns = {
            'เชฟเอก': ['morning', 'morning', 'split', 'morning', 'morning', 'split', None],
            'พี่กุ้ง': ['morning', 'split', 'morning', 'morning', 'split', None, 'morning'],
            'น้องแนน': ['evening', 'evening', 'evening', None, 'morning', 'evening', 'evening'],
            'ชาย': ['split', 'split', None, 'split', 'split', 'evening', 'split'],
            'มิ้นท์': ['evening', None, 'evening', 'evening', 'evening', 'split', 'evening'],
            'พี่แอ๋ม': ['full', 'full', 'full', 'full', 'full', None, None],
            'น้องเบิร์ด': ['morning', 'morning', 'morning', 'morning', 'morning', 'morning', None],
        }
        start_of_week = today - timedelta(days=today.weekday())
        shift_count = 0
        for nick, pattern in shift_patterns.items():
            emp = emp_objs.get(nick)
            if not emp:
                continue
            for i, stype in enumerate(pattern):
                if stype is None:
                    continue
                d = start_of_week + timedelta(days=i)
                ShiftSchedule.objects.get_or_create(
                    employee=emp, date=d,
                    defaults={'shift_type': stype},
                )
                shift_count += 1
        self.stdout.write(f'  ✅ สร้างกะ {shift_count} กะ')

        # Attendance — 10 วันย้อนหลัง
        att_count = 0
        for d_offset in range(10):
            d = today - timedelta(days=d_offset)
            for nick, emp in emp_objs.items():
                if random.random() < 0.15:  # 15% chance หยุด
                    continue
                if emp.position in ('chef', 'sous_chef', 'cook', 'cashier'):
                    h_in = random.randint(6, 8)
                    h_out = h_in + random.randint(8, 10)
                else:
                    h_in = random.randint(9, 11)
                    h_out = h_in + random.randint(7, 9)

                att, created = Attendance.objects.get_or_create(
                    employee=emp, date=d,
                    defaults={
                        'clock_in': time(hour=h_in, minute=random.randint(0, 30)),
                        'clock_out': time(hour=min(h_out, 23), minute=random.randint(0, 59)),
                    },
                )
                if created:
                    att.calculate_hours()
                    att.save()
                    att_count += 1
        self.stdout.write(f'  ✅ สร้าง Attendance {att_count} รายการ')

        # Payroll — เดือนนี้
        for nick, emp in emp_objs.items():
            pr, created = PayrollRecord.objects.get_or_create(
                employee=emp, month=today.month, year=today.year,
            )
            if created:
                pr.calculate()
                pr.save()
        self.stdout.write(f'  ✅ สร้าง Payroll {len(emp_objs)} รายการ')

        # =================================================================
        # Phase 7 — Reports (DailySalesRecord + MonthlyPL)
        # =================================================================
        from reports.models import ACUsageLog, DailySalesRecord, MonthlyPL

        for d_offset in range(10):
            d = today - timedelta(days=d_offset)
            # Sum actual POS orders for this date
            day_orders = Order.objects.filter(
                tenant=tenant, status='paid',
                opened_at__date=d,
            )
            dine_rev = sum(o.total for o in day_orders)
            bev_rev = Decimal(str(random.randint(800, 2500)))
            bf_rev = Decimal(str(random.randint(2000, 5000)))
            event_rev = Decimal('0')
            if d_offset == 5:  # งานแต่ง
                event_rev = Decimal('12480')
            total_rev = dine_rev + bev_rev + bf_rev + event_rev
            covers = day_orders.count() * 2 + random.randint(5, 15)

            DailySalesRecord.objects.get_or_create(
                tenant=tenant, date=d,
                defaults={
                    'dine_in_revenue': dine_rev,
                    'beverage_revenue': bev_rev,
                    'bf_revenue': bf_rev,
                    'event_revenue': event_rev,
                    'total_revenue': total_rev,
                    'total_covers': covers,
                    'avg_check': total_rev / covers if covers else 0,
                    'food_cost_actual': total_rev * Decimal('0.32'),
                    'food_cost_theoretical': total_rev * Decimal('0.29'),
                },
            )
        self.stdout.write('  ✅ สร้าง DailySalesRecord 10 วัน')

        # Monthly P&L
        total_month_rev = sum(
            ds.total_revenue for ds in
            DailySalesRecord.objects.filter(tenant=tenant, date__month=today.month, date__year=today.year)
        )
        total_labour = sum(pr.gross_pay for pr in PayrollRecord.objects.filter(
            employee__tenant=tenant, month=today.month, year=today.year
        ))
        fc_actual = total_month_rev * Decimal('0.32')
        fc_theo = total_month_rev * Decimal('0.29')
        waste = Decimal('3200')
        electricity = Decimal('8500')
        other_exp = Decimal('12000')

        pl, pl_created = MonthlyPL.objects.get_or_create(
            tenant=tenant, month=today.month, year=today.year,
            defaults={
                'dine_in_revenue': total_month_rev * Decimal('0.55'),
                'beverage_revenue': total_month_rev * Decimal('0.12'),
                'bf_revenue': total_month_rev * Decimal('0.25'),
                'event_revenue': total_month_rev * Decimal('0.08'),
                'total_revenue': total_month_rev,
                'food_cost_theoretical': fc_theo,
                'food_cost_actual': fc_actual,
                'waste_cost': waste,
                'labour_cost': total_labour,
                'electricity_cost': electricity,
                'other_expenses': other_exp,
            },
        )
        if pl_created:
            pl.calculate()
            pl.save()
        self.stdout.write('  ✅ สร้าง MonthlyPL')

        # =================================================================
        # Phase 8 — Sensibo AC Usage Logs
        # =================================================================
        ac_count = 0
        for d_offset in range(7):
            d = today - timedelta(days=d_offset)
            for hour in range(8, 23):
                ac_on = 9 <= hour <= 22
                power = Decimal('1500') if ac_on else Decimal('0')
                temp = Decimal(str(random.randint(24, 28)))
                humidity = Decimal(str(random.randint(55, 75)))
                # 4.5 THB/kWh, 1500W = 1.5kW, interval = 1hr
                cost = Decimal('6.75') if ac_on else Decimal('0')

                ts = timezone.make_aware(
                    datetime.datetime.combine(d, time(hour=hour, minute=0))
                )
                ACUsageLog.objects.get_or_create(
                    tenant=tenant, device_id='SENSIBO-SARKAO-01', timestamp=ts,
                    defaults={
                        'power_watts': power,
                        'temperature': temp,
                        'humidity': humidity,
                        'ac_on': ac_on,
                        'estimated_cost_thb': cost,
                    },
                )
                ac_count += 1
        self.stdout.write(f'  ✅ สร้าง AC Usage Logs {ac_count} records')

        # =================================================================
        # Done!
        # =================================================================
        self.stdout.write(self.style.SUCCESS(
            '\n🎉 Mock data ร้านอาหารใต้สารข้าว พร้อมใช้งานทุก Phase!\n'
            '   Login: admin / jaan1234\n'
            '   Staff: somchai, nong, view / jaan1234\n'
            '\n'
            '   📊 Stock: 36 วัตถุดิบ, 10 recipes, 15 เมนู\n'
            '   💳 POS: ~70 orders, 10 โต๊ะ, 16 upsell rules\n'
            '   🎪 Events: 3 งาน (แต่ง/เลี้ยงรุ่น/สัมมนา)\n'
            '   🏨 Hotel: 9 ห้อง, 5 room charges, 7 วัน BF\n'
            '   👥 HR: 7 พนักงาน, กะ+เวลา+payroll\n'
            '   📈 Reports: 10 วัน daily sales, P&L\n'
            '   ❄️ AC/IoT: 7 วัน Sensibo logs\n'
        ))
