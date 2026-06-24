"""
POS Signals — ตัวกระตุ้นอัตโนมัติ
เมื่อออเดอร์เปลี่ยนสถานะเป็น "ชำระแล้ว" ระบบจะ:
  1. ตัดสต็อกวัตถุดิบตามสูตร (FIFO) อัตโนมัติ
  2. อัปเดตยอดขายรายวัน (DailySalesRecord)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from core.notify import audit

from .models import Order
from .services import deplete_stock_for_order, recompute_daily_sales


@receiver(post_save, sender=Order, dispatch_uid='pos_order_paid_automation')
def on_order_paid(sender, instance, **kwargs):
    # ทำงานเฉพาะตอนชำระเงินแล้ว และยังไม่เคยตัดสต็อก (กันทำซ้ำ/กัน recursion)
    if instance.status != 'paid' or instance.stock_depleted:
        return

    deplete_stock_for_order(instance, user=instance.created_by)
    # ใช้วันที่ตามโซนเวลาไทยของ opened_at (ไม่ใช่ UTC date) ให้ตรงกับ __date lookup
    business_date = timezone.localtime(instance.opened_at).date()
    recompute_daily_sales(instance.tenant, business_date)
    audit(
        'order.paid', user=instance.created_by, tenant=instance.tenant,
        model_name='Order', object_id=instance.pk,
        summary=f'ชำระเงินออเดอร์ {instance.order_number} ฿{instance.total} + ตัดสต็อกอัตโนมัติ',
    )
