"""Tests — core (ศูนย์แจ้งเตือน + audit log)"""
from django.test import TestCase

from accounts.models import Tenant, User
from core.models import AuditLog, Notification
from core.notify import audit, notify


class NotifyTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ร้าน', slug='t')

    def test_notify_creates_db_record(self):
        n = notify(self.tenant, 'ทดสอบ', 'รายละเอียด', level='warning', category='stock')
        self.assertIsInstance(n, Notification)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(n.level, 'warning')
        self.assertFalse(n.is_read)

    def test_notify_external_push_silent_without_config(self):
        # ไม่ตั้งค่า LINE → ต้องไม่ error และยังสร้าง DB record ปกติ
        n = notify(self.tenant, 'ไม่มี token')
        self.assertEqual(n.title, 'ไม่มี token')


class AuditTest(TestCase):
    def test_audit_records_action(self):
        tenant = Tenant.objects.create(name='ร้าน', slug='t')
        user = User.objects.create_user(username='owner', password='x', tenant=tenant)
        log = audit('order.paid', user=user, tenant=tenant, model_name='Order',
                    object_id=5, summary='จ่ายเงิน')
        self.assertIsInstance(log, AuditLog)
        self.assertEqual(log.action, 'order.paid')
        self.assertEqual(log.user, user)
        self.assertEqual(log.object_id, '5')

    def test_audit_handles_anonymous(self):
        log = audit('system.cron', user=None, summary='cron run')
        self.assertIsNone(log.user)
