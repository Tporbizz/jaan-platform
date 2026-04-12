import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class EventSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'ร่าง'
        ACTIVE = 'active', 'กำลังขาย'
        CLOSED = 'closed', 'ปิดแล้ว'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='event_sessions', verbose_name='ร้าน')
    name = models.CharField('ชื่องาน', max_length=200)
    date = models.DateField('วันที่', default=timezone.now)
    location = models.CharField('สถานที่', max_length=200, blank=True)
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.DRAFT)
    session_token = models.UUIDField('Token', default=uuid.uuid4, unique=True, editable=False)
    menu_snapshot = models.JSONField('สแนปช็อตเมนู', default=list)
    total_revenue = models.DecimalField('รายได้รวม', max_digits=12, decimal_places=2, default=0)
    total_orders = models.PositiveIntegerField('จำนวนออเดอร์', default=0)
    notes = models.TextField('หมายเหตุ', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='สร้างโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'events_eventsession'
        verbose_name = 'งานอีเวนต์'
        verbose_name_plural = 'งานอีเวนต์'
        ordering = ['-date']

    def __str__(self):
        return f"{self.name} ({self.date})"

    def recalculate_totals(self):
        orders = self.orders.filter(status='paid')
        self.total_revenue = sum(o.total for o in orders)
        self.total_orders = orders.count()
        self.save(update_fields=['total_revenue', 'total_orders'])


class EventOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'รอชำระ'
        PAID = 'paid', 'ชำระแล้ว'
        CANCELLED = 'cancelled', 'ยกเลิก'

    session = models.ForeignKey(EventSession, on_delete=models.CASCADE, related_name='orders', verbose_name='งานอีเวนต์')
    order_number = models.CharField('เลขออเดอร์', max_length=20)
    customer_name = models.CharField('ชื่อลูกค้า', max_length=100, blank=True)
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField('ยอดก่อนหัก', max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField('ยอดรวม', max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField('วิธีชำระ', max_length=20, blank=True)
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'events_eventorder'
        verbose_name = 'ออเดอร์อีเวนต์'
        verbose_name_plural = 'ออเดอร์อีเวนต์'
        ordering = ['-created_at']

    def __str__(self):
        return f"EV-{self.order_number}"

    def recalculate(self):
        self.subtotal = sum(i.line_total for i in self.items.all())
        self.total = self.subtotal
        self.save(update_fields=['subtotal', 'total'])


class EventOrderItem(models.Model):
    order = models.ForeignKey(EventOrder, on_delete=models.CASCADE, related_name='items', verbose_name='ออเดอร์')
    menu_item_name = models.CharField('ชื่อเมนู', max_length=200)
    menu_item_id = models.IntegerField('ID เมนู', null=True, blank=True)
    quantity = models.PositiveIntegerField('จำนวน', default=1)
    unit_price = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'events_eventorderitem'
        verbose_name = 'รายการออเดอร์อีเวนต์'
        verbose_name_plural = 'รายการออเดอร์อีเวนต์'

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.menu_item_name} x{self.quantity}"
