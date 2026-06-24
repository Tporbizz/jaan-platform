"""
Tests — POS Automation Engine (Wave 1)
ทดสอบว่า "ขายอาหาร → ตัดสต็อกอัตโนมัติ" ทำงานถูกต้องและไม่ตัดซ้ำ
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Tenant, User
from restaurant.models import (
    Category, Unit, Item, LotBatch, Recipe, RecipeItem, MenuItem,
    StockMovement,
)
from pos.models import Table, Order, OrderItem


class StockDepletionTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้านทดสอบ', slug='test')
        self.unit = Unit.objects.create(tenant=self.tenant, name='กรัม', abbreviation='g')
        self.cat = Category.objects.create(tenant=self.tenant, name='เนื้อสัตว์')

        # วัตถุดิบ: สต็อก 1000g, ต้นทุนปัจจุบัน 0.50/g
        self.pork = Item.objects.create(
            tenant=self.tenant, name='หมูสับ', category=self.cat, unit=self.unit,
            current_stock=Decimal('1000'), cost_per_unit=Decimal('0.50'),
        )
        # Lot FIFO: 600g @0.40 (หมดอายุก่อน), 600g @0.60
        LotBatch.objects.create(
            tenant=self.tenant, item=self.pork, quantity=Decimal('600'),
            cost_per_unit=Decimal('0.40'), received_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timezone.timedelta(days=2),
        )
        LotBatch.objects.create(
            tenant=self.tenant, item=self.pork, quantity=Decimal('600'),
            cost_per_unit=Decimal('0.60'), received_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timezone.timedelta(days=10),
        )

        # สูตร: ทำได้ 1 จาน ใช้หมู 200g
        self.recipe = Recipe.objects.create(tenant=self.tenant, name='ผัดกะเพราหมู', portions=1)
        RecipeItem.objects.create(
            recipe=self.recipe, item=self.pork, quantity=Decimal('200'), unit=self.unit,
        )
        self.menu = MenuItem.objects.create(
            tenant=self.tenant, name='กะเพราหมู', recipe=self.recipe,
            selling_price=Decimal('80'),
        )
        self.table = Table.objects.create(tenant=self.tenant, number='1')

    def _make_paid_order(self, qty=2):
        order = Order.objects.create(
            tenant=self.tenant, table=self.table, order_number='T001',
            guest_count=2, total=Decimal('160'), subtotal=Decimal('160'),
        )
        OrderItem.objects.create(
            order=order, menu_item=self.menu, quantity=qty,
            unit_price=Decimal('80'),
        )
        order.status = 'paid'
        order.closed_at = timezone.now()
        order.save()  # ← signal ควรตัดสต็อกอัตโนมัติตรงนี้
        return order

    def test_paying_order_depletes_stock(self):
        self._make_paid_order(qty=2)  # 2 จาน × 200g = 400g
        self.pork.refresh_from_db()
        self.assertEqual(self.pork.current_stock, Decimal('600'))  # 1000 - 400

    def test_creates_out_stock_movement(self):
        order = self._make_paid_order(qty=2)
        mv = StockMovement.objects.filter(item=self.pork, movement_type='out')
        self.assertEqual(mv.count(), 1)
        self.assertEqual(mv.first().quantity, Decimal('400'))
        self.assertIn(order.order_number, mv.first().reference)

    def test_fifo_cost_snapshot(self):
        # 400g FIFO: 400g มาจาก Lot 0.40 ก่อน = 160 บาท
        order = self._make_paid_order(qty=2)
        oi = order.items.first()
        self.assertEqual(oi.cost_snapshot, Decimal('160.00'))

    def test_lots_consumed_fifo(self):
        self._make_paid_order(qty=2)  # 400g
        lots = LotBatch.objects.filter(item=self.pork).order_by('expiry_date')
        self.assertEqual(lots[0].quantity, Decimal('200'))  # 600 - 400
        self.assertEqual(lots[1].quantity, Decimal('600'))  # ยังไม่แตะ

    def test_idempotent_no_double_depletion(self):
        order = self._make_paid_order(qty=2)
        order.refresh_from_db()
        order.save()  # save ซ้ำ — ต้องไม่ตัดสต็อกอีก
        order.save()
        self.pork.refresh_from_db()
        self.assertEqual(self.pork.current_stock, Decimal('600'))
        self.assertEqual(
            StockMovement.objects.filter(item=self.pork, movement_type='out').count(), 1,
        )

    def test_daily_sales_record_created(self):
        from reports.models import DailySalesRecord
        order = self._make_paid_order(qty=2)
        rec = DailySalesRecord.objects.get(tenant=self.tenant, date=order.opened_at.date())
        self.assertEqual(rec.total_revenue, Decimal('160'))
        self.assertEqual(rec.food_cost_actual, Decimal('160.00'))

    def test_menu_without_recipe_does_not_crash(self):
        plain = MenuItem.objects.create(
            tenant=self.tenant, name='น้ำเปล่า', selling_price=Decimal('20'),
        )
        order = Order.objects.create(
            tenant=self.tenant, table=self.table, order_number='T002',
            guest_count=1, total=Decimal('20'), subtotal=Decimal('20'),
        )
        OrderItem.objects.create(order=order, menu_item=plain, quantity=1, unit_price=Decimal('20'))
        order.status = 'paid'
        order.save()
        order.refresh_from_db()
        self.assertTrue(order.stock_depleted)


class PosRouteSmokeTest(TestCase):
    """กัน regression: ทุกหน้า POS ต้องโหลด 200 ไม่ใช่ 500
    (เคยพลาด decorator ไปติด helper ทำให้ 'Tenant' object has no attribute 'user')"""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='smoke')
        self.user = User.objects.create_user(
            username='mgr', password='x', tenant=self.tenant,
            role='manager', department='manager',
        )
        self.client.force_login(self.user)
        Table.objects.create(tenant=self.tenant, number='1')

    def test_pos_pages_load(self):
        from django.urls import reverse
        for name in ['pos:pos_dashboard', 'pos:table_map', 'pos:table_grid',
                     'pos:kitchen_display', 'pos:kitchen_grid']:
            with self.subTest(view=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 200, f'{name} -> {r.status_code}')

    def test_dashboard_pages_load(self):
        for url in ['/dashboard/', '/dashboard/kpis/']:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, f'{url} -> {r.status_code}')
