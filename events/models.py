import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class EventSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'ร่าง'
        ACTIVE = 'active', 'กำลังขาย'
        CLOSED = 'closed', 'ปิดแล้ว'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='event_sessions')
    name = models.CharField(max_length=200)
    date = models.DateField(default=timezone.now)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    menu_snapshot = models.JSONField(default=list)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'events_eventsession'
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

    session = models.ForeignKey(EventSession, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'events_eventorder'
        ordering = ['-created_at']

    def __str__(self):
        return f"EV-{self.order_number}"

    def recalculate(self):
        self.subtotal = sum(i.line_total for i in self.items.all())
        self.total = self.subtotal
        self.save(update_fields=['subtotal', 'total'])


class EventOrderItem(models.Model):
    order = models.ForeignKey(EventOrder, on_delete=models.CASCADE, related_name='items')
    menu_item_name = models.CharField(max_length=200)
    menu_item_id = models.IntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'events_eventorderitem'

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.menu_item_name} x{self.quantity}"
