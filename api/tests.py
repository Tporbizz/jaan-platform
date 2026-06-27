"""Tests — REST API (JWT auth, tenant scoping) + CSV export"""
import json
from decimal import Decimal

from django.test import TestCase

from accounts.models import Tenant, User
from restaurant.models import Category, Unit, Item


class ApiAuthTest(TestCase):
    def setUp(self):
        self.t1 = Tenant.objects.create(name='ร้าน A', slug='a')
        self.t2 = Tenant.objects.create(name='ร้าน B', slug='b')
        self.u1 = User.objects.create_user(username='a1', password='pw12345', tenant=self.t1, role='owner', department='gm')
        unit = Unit.objects.create(tenant=self.t1, name='g', abbreviation='g')
        cat = Category.objects.create(tenant=self.t1, name='ของสด')
        Item.objects.create(tenant=self.t1, name='หมูบด A', category=cat, unit=unit, cost_per_unit=Decimal('1'))
        # ของร้าน B
        u2b = Unit.objects.create(tenant=self.t2, name='g', abbreviation='g')
        c2b = Category.objects.create(tenant=self.t2, name='ของสด')
        Item.objects.create(tenant=self.t2, name='ปลา B', category=c2b, unit=u2b, cost_per_unit=Decimal('1'))

    def _token(self):
        r = self.client.post('/api/accounts/token/',
                             data=json.dumps({'username': 'a1', 'password': 'pw12345'}),
                             content_type='application/json')
        return r.json()['access']

    def test_requires_auth(self):
        r = self.client.get('/api/v1/items/')
        self.assertEqual(r.status_code, 401)  # 401 ไม่ใช่ redirect

    def test_jwt_access(self):
        tok = self._token()
        r = self.client.get('/api/v1/summary/', HTTP_AUTHORIZATION=f'Bearer {tok}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('today_revenue', r.json())

    def test_tenant_isolation(self):
        tok = self._token()
        r = self.client.get('/api/v1/items/', HTTP_AUTHORIZATION=f'Bearer {tok}')
        names = [it['name'] for it in r.json()['results']]
        self.assertIn('หมูบด A', names)
        self.assertNotIn('ปลา B', names)  # ไม่เห็นข้อมูลร้านอื่น


class ExportTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='exp')
        self.owner = User.objects.create_user(username='o', password='x', tenant=self.tenant, role='owner', department='gm')
        unit = Unit.objects.create(tenant=self.tenant, name='g', abbreviation='g')
        cat = Category.objects.create(tenant=self.tenant, name='ของสด')
        Item.objects.create(tenant=self.tenant, code='FF-1', name='หมูบด', category=cat, unit=unit, cost_per_unit=Decimal('1'), current_stock=Decimal('5'))
        self.client.force_login(self.owner)

    def test_stock_export_csv(self):
        r = self.client.get('/stock/export/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode('utf-8-sig')
        self.assertIn('หมูบด', body)
        self.assertIn('FF-1', body)

    def test_pl_export_csv(self):
        r = self.client.get('/reports/pl/export/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
