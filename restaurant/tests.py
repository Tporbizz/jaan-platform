"""
Tests — Restaurant Automation (Wave 2)
สั่งซื้ออัตโนมัติ + สแกนหมดอายุ + ปิดยอด P&L
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Tenant
from restaurant.models import (
    Category, Unit, Item, Supplier, LotBatch, PurchaseOrder, POItem,
)
from restaurant.services import (
    auto_generate_reorder_pos, scan_expiring_lots, scan_low_stock,
)


class AutoReorderTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='t')
        self.unit = Unit.objects.create(tenant=self.tenant, name='กก.', abbreviation='kg')
        self.cat = Category.objects.create(tenant=self.tenant, name='ผัก')
        self.sup = Supplier.objects.create(tenant=self.tenant, name='เจ๊แดงผักสด')

        # ต่ำกว่าขั้นต่ำ: stock 2 < min 10, max 20 → ควรสั่ง 18
        self.kale = Item.objects.create(
            tenant=self.tenant, name='คะน้า', category=self.cat, unit=self.unit,
            current_stock=Decimal('2'), min_stock=Decimal('10'), max_stock=Decimal('20'),
            cost_per_unit=Decimal('40'), default_supplier=self.sup,
        )
        # ปกติ: stock 50 > min 10 → ไม่สั่ง
        Item.objects.create(
            tenant=self.tenant, name='พริก', category=self.cat, unit=self.unit,
            current_stock=Decimal('50'), min_stock=Decimal('10'),
            cost_per_unit=Decimal('80'), default_supplier=self.sup,
        )

    def test_creates_draft_po_for_low_stock(self):
        pos = auto_generate_reorder_pos(self.tenant)
        self.assertEqual(len(pos), 1)
        po = pos[0]
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.supplier, self.sup)
        self.assertEqual(po.items.count(), 1)
        item_line = po.items.first()
        self.assertEqual(item_line.item, self.kale)
        self.assertEqual(item_line.quantity, Decimal('18'))  # 20 - 2

    def test_skips_item_already_in_open_po(self):
        # มี PO ค้างอยู่แล้วสำหรับคะน้า → ไม่สั่งซ้ำ
        existing = PurchaseOrder.objects.create(
            tenant=self.tenant, po_number='X1', supplier=self.sup, status='sent',
        )
        POItem.objects.create(purchase_order=existing, item=self.kale,
                              quantity=Decimal('18'), unit_price=Decimal('40'))
        pos = auto_generate_reorder_pos(self.tenant)
        self.assertEqual(len(pos), 0)

    def test_item_without_supplier_skipped(self):
        Item.objects.create(
            tenant=self.tenant, name='โหระพา', category=self.cat, unit=self.unit,
            current_stock=Decimal('0'), min_stock=Decimal('5'), cost_per_unit=Decimal('30'),
        )
        pos = auto_generate_reorder_pos(self.tenant)
        # สร้างเฉพาะคะน้า (มี supplier) — โหระพาถูกข้าม
        all_items = [li.item.name for po in pos for li in po.items.all()]
        self.assertIn('คะน้า', all_items)
        self.assertNotIn('โหระพา', all_items)

    def test_scan_low_stock(self):
        low = scan_low_stock(self.tenant)
        self.assertEqual({i.name for i in low}, {'คะน้า'})


class ExpiryScanTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='t')
        self.unit = Unit.objects.create(tenant=self.tenant, name='กก.', abbreviation='kg')
        self.cat = Category.objects.create(tenant=self.tenant, name='ของสด')
        self.item = Item.objects.create(
            tenant=self.tenant, name='ปลา', category=self.cat, unit=self.unit,
            cost_per_unit=Decimal('100'),
        )
        today = timezone.now().date()
        # หมดอายุพรุ่งนี้ (มีของ) → ต้องเจอ
        LotBatch.objects.create(tenant=self.tenant, item=self.item, quantity=Decimal('5'),
                                cost_per_unit=Decimal('100'), expiry_date=today + timezone.timedelta(days=1))
        # หมดอายุอีก 30 วัน → ไม่เจอ
        LotBatch.objects.create(tenant=self.tenant, item=self.item, quantity=Decimal('5'),
                                cost_per_unit=Decimal('100'), expiry_date=today + timezone.timedelta(days=30))
        # ใกล้หมดอายุแต่ของหมดแล้ว (qty 0) → ไม่เจอ
        LotBatch.objects.create(tenant=self.tenant, item=self.item, quantity=Decimal('0'),
                                cost_per_unit=Decimal('100'), expiry_date=today)

    def test_scan_expiring_only_within_window_with_stock(self):
        expiring = scan_expiring_lots(self.tenant, days=3)
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].quantity, Decimal('5'))


class MonthlyPLTest(TestCase):
    def test_rollup_aggregates_revenue_and_costs(self):
        from reports.models import DailySalesRecord
        from reports.services import rollup_monthly_pl

        tenant = Tenant.objects.create(name='ร้าน', slug='t')
        DailySalesRecord.objects.create(
            tenant=tenant, date=timezone.datetime(2027, 1, 5).date(),
            total_revenue=Decimal('10000'), dine_in_revenue=Decimal('8000'),
            beverage_revenue=Decimal('2000'), food_cost_actual=Decimal('3000'),
        )
        DailySalesRecord.objects.create(
            tenant=tenant, date=timezone.datetime(2027, 1, 6).date(),
            total_revenue=Decimal('5000'), dine_in_revenue=Decimal('5000'),
            food_cost_actual=Decimal('1500'),
        )
        pl = rollup_monthly_pl(tenant, 1, 2027)
        self.assertEqual(pl.total_revenue, Decimal('15000'))
        self.assertEqual(pl.food_cost_actual, Decimal('4500'))
        self.assertEqual(pl.food_cost_pct, Decimal('30.00'))  # 4500/15000
        self.assertEqual(pl.gross_profit, Decimal('10500'))   # 15000 - 4500

    def test_rollup_idempotent(self):
        from reports.models import DailySalesRecord, MonthlyPL
        from reports.services import rollup_monthly_pl

        tenant = Tenant.objects.create(name='ร้าน', slug='t')
        DailySalesRecord.objects.create(
            tenant=tenant, date=timezone.datetime(2027, 2, 1).date(),
            total_revenue=Decimal('1000'), food_cost_actual=Decimal('300'),
        )
        rollup_monthly_pl(tenant, 2, 2027)
        rollup_monthly_pl(tenant, 2, 2027)
        self.assertEqual(MonthlyPL.objects.filter(tenant=tenant, month=2, year=2027).count(), 1)


class MenuImageUploadTest(TestCase):
    """อัปโหลดรูปเมนูผ่านหน้าจัดการเมนู"""

    def setUp(self):
        from accounts.models import User
        self.tenant = Tenant.objects.create(name='ร้าน', slug='img')
        self.owner = User.objects.create_user(
            username='owner', password='x', tenant=self.tenant,
            role='owner', department='gm',
        )
        self.client.force_login(self.owner)

    def test_menu_save_accepts_image(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from restaurant.models import MenuItem

        buf = io.BytesIO()
        Image.new('RGB', (10, 10), (200, 150, 50)).save(buf, 'JPEG')
        upload = SimpleUploadedFile('dish.jpg', buf.getvalue(), content_type='image/jpeg')

        r = self.client.post('/settings/menu/save/', {
            'name': 'ผัดไทยกุ้งแม่น้ำ', 'selling_price': '550',
            'menu_category': 'single_dish', 'sort_order': '0',
            'image': upload,
        })
        self.assertEqual(r.status_code, 302)
        menu = MenuItem.objects.get(name='ผัดไทยกุ้งแม่น้ำ')
        self.assertTrue(menu.image)
        menu.image.delete(save=False)  # cleanup ไฟล์ทดสอบ


class MarketListImportTest(TestCase):
    """นำเข้า Market List จริง + แก้สูตรด้วยวัตถุดิบที่นำเข้า"""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='ml')

    def test_import_creates_items_with_code_and_cost(self):
        from django.core.management import call_command
        from restaurant.models import Item
        call_command('import_market_list', tenant=self.tenant.id, verbosity=0)
        # ควรนำเข้าหลายร้อยรายการ
        self.assertGreater(Item.objects.filter(tenant=self.tenant).count(), 500)
        # ตัวอย่างจริง: ไข่ไก่ เบอร์ 3 = FF-0002
        egg = Item.objects.filter(tenant=self.tenant, code='FF-0002').first()
        self.assertIsNotNone(egg)
        self.assertGreater(egg.cost_per_unit, 0)

    def test_import_idempotent(self):
        from django.core.management import call_command
        from restaurant.models import Item
        call_command('import_market_list', tenant=self.tenant.id, verbosity=0)
        n1 = Item.objects.filter(tenant=self.tenant).count()
        call_command('import_market_list', tenant=self.tenant.id, verbosity=0)
        n2 = Item.objects.filter(tenant=self.tenant).count()
        self.assertEqual(n1, n2)  # รันซ้ำไม่เพิ่มจำนวน


class RecipeEditTest(TestCase):
    def setUp(self):
        from accounts.models import User
        self.tenant = Tenant.objects.create(name='ร้าน', slug='re')
        self.user = User.objects.create_user(username='gm', password='x', tenant=self.tenant,
                                              role='owner', department='gm')
        self.client.force_login(self.user)
        self.unit = Unit.objects.create(tenant=self.tenant, name='กรัม', abbreviation='g')
        self.cat = Category.objects.create(tenant=self.tenant, name='เนื้อสัตว์')
        self.pork = Item.objects.create(tenant=self.tenant, code='FF-0009', name='หมูบด',
                                        category=self.cat, unit=self.unit, cost_per_unit=Decimal('0.12'))
        from restaurant.models import Recipe
        self.recipe = Recipe.objects.create(tenant=self.tenant, name='ผัดกะเพรา', portions=1)

    def test_add_ingredient_updates_cost(self):
        from restaurant.models import Recipe
        r = self.client.post(f'/settings/recipes/{self.recipe.id}/add-ingredient/', {
            'item_id': self.pork.id, 'quantity': '200', 'unit_id': self.unit.id, 'notes': '',
        })
        self.assertEqual(r.status_code, 302)
        recipe = Recipe.objects.get(id=self.recipe.id)
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.calculate_cost(), Decimal('24.00'))  # 200 * 0.12

    def test_recipe_detail_has_search_data(self):
        resp = self.client.get(f'/settings/recipes/{self.recipe.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'items-data')
        self.assertContains(resp, 'ing-search')


class StockSearchTest(TestCase):
    """หน้าสต็อกค้นหา/กรองได้ (รองรับวัตถุดิบหลายร้อยรายการ)"""

    def setUp(self):
        from accounts.models import User
        self.tenant = Tenant.objects.create(name='ร้าน', slug='ss2')
        self.user = User.objects.create_user(username='gm', password='x', tenant=self.tenant,
                                              role='owner', department='gm')
        self.client.force_login(self.user)
        self.unit = Unit.objects.create(tenant=self.tenant, name='กรัม', abbreviation='g')
        self.meat = Category.objects.create(tenant=self.tenant, name='เนื้อสัตว์')
        self.veg = Category.objects.create(tenant=self.tenant, name='ผัก')
        Item.objects.create(tenant=self.tenant, code='FF-0009', name='หมูบด', category=self.meat,
                            unit=self.unit, cost_per_unit=Decimal('0.12'),
                            current_stock=Decimal('5'), min_stock=Decimal('10'))
        Item.objects.create(tenant=self.tenant, code='FF-0016', name='คะน้า', category=self.veg,
                            unit=self.unit, cost_per_unit=Decimal('0.08'), current_stock=Decimal('50'))

    def test_search_by_name(self):
        r = self.client.get('/stock/?q=หมู')
        self.assertContains(r, 'หมูบด')
        self.assertNotContains(r, '>คะน้า<')

    def test_search_by_code(self):
        r = self.client.get('/stock/?q=FF-0009')
        self.assertEqual(r.context['item_match_count'], 1)

    def test_filter_status_low(self):
        r = self.client.get('/stock/?status=low')
        self.assertEqual(r.context['item_match_count'], 1)  # เฉพาะหมูบด (5<10)

    def test_filter_category(self):
        r = self.client.get(f'/stock/?cat={self.veg.id}')
        self.assertEqual(r.context['item_match_count'], 1)  # เฉพาะคะน้า
