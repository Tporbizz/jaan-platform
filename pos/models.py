from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# Table (โต๊ะ)
# =============================================================================

class Table(models.Model):
    class Status(models.TextChoices):
        EMPTY = 'empty', 'ว่าง'
        OCCUPIED = 'occupied', 'มีลูกค้า'
        BILL_PENDING = 'bill_pending', 'รอเก็บเงิน'
        RESERVED = 'reserved', 'จอง'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='tables')
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=50, blank=True, help_text='เช่น โต๊ะริมน้ำ, ห้อง VIP')
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EMPTY)
    zone = models.CharField(max_length=50, blank=True, help_text='โซน เช่น ในร้าน, ริมน้ำ, ชั้น 2')
    grid_x = models.PositiveIntegerField(default=0, help_text='ตำแหน่งบน floor plan')
    grid_y = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'pos_table'
        ordering = ['sort_order', 'number']

    def __str__(self):
        return f"โต๊ะ {self.number}" + (f" ({self.name})" if self.name else "")


# =============================================================================
# Order + OrderItem
# =============================================================================

class Order(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'เปิดอยู่'
        SENT = 'sent', 'ส่งครัวแล้ว'
        SERVED = 'served', 'เสิร์ฟแล้ว'
        BILL = 'bill', 'รอเก็บเงิน'
        PAID = 'paid', 'ชำระแล้ว'
        CANCELLED = 'cancelled', 'ยกเลิก'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='orders')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # Guest info (สำหรับ upsell engine)
    guest_count = models.PositiveIntegerField(default=1)
    men_count = models.PositiveIntegerField(default=0)
    women_count = models.PositiveIntegerField(default=0)
    children_count = models.PositiveIntegerField(default=0)
    senior_count = models.PositiveIntegerField(default=0)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='orders_created')

    class Meta:
        db_table = 'pos_order'
        ordering = ['-opened_at']

    def __str__(self):
        return f"Order #{self.order_number} — โต๊ะ {self.table.number if self.table else 'N/A'}"

    def recalculate(self):
        items = self.items.filter(is_voided=False)
        self.subtotal = sum(item.line_total for item in items)
        self.total = self.subtotal - self.discount + self.service_charge + self.vat
        self.save(update_fields=['subtotal', 'total'])

    @property
    def duration_minutes(self):
        end = self.closed_at or timezone.now()
        return int((end - self.opened_at).total_seconds() / 60)

    @property
    def avg_check(self):
        if self.guest_count:
            return self.subtotal / self.guest_count
        return self.subtotal


class OrderItem(models.Model):
    class ItemStatus(models.TextChoices):
        PENDING = 'pending', 'รอส่งครัว'
        SENT = 'sent', 'ส่งครัวแล้ว'
        PREPARING = 'preparing', 'กำลังทำ'
        READY = 'ready', 'พร้อมเสิร์ฟ'
        SERVED = 'served', 'เสิร์ฟแล้ว'
        VOIDED = 'voided', 'ยกเลิก'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    special_request = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING)
    is_voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    served_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pos_orderitem'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"

    @property
    def line_total(self):
        if self.is_voided:
            return 0
        return self.quantity * self.unit_price


# =============================================================================
# Kitchen Ticket
# =============================================================================

class KitchenTicket(models.Model):
    class TicketStatus(models.TextChoices):
        PENDING = 'pending', 'รอทำ'
        IN_PROGRESS = 'in_progress', 'กำลังทำ'
        DONE = 'done', 'เสร็จ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='kitchen_tickets')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='kitchen_tickets')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True)
    ticket_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.PENDING)
    prepared_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kitchen_tickets', help_text='เชฟ/คนครัวที่รับผิดชอบ',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'pos_kitchenticket'
        ordering = ['-created_at']

    def __str__(self):
        return f"KT-{self.ticket_number} (โต๊ะ {self.table.number if self.table else 'N/A'})"


class KitchenTicketItem(models.Model):
    ticket = models.ForeignKey(KitchenTicket, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='ticket_items')
    quantity = models.PositiveIntegerField(default=1)
    special_request = models.CharField(max_length=200, blank=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        db_table = 'pos_kitchenticketitem'

    def __str__(self):
        return f"{self.order_item.menu_item.name} x{self.quantity}"


# =============================================================================
# Upsell Engine
# =============================================================================

class MenuUpsellRule(models.Model):
    class ProfileType(models.TextChoices):
        COUPLE = 'couple', 'คู่รัก (1ช+1ญ)'
        HAS_CHILDREN = 'has_children', 'มีเด็ก'
        HAS_SENIOR = 'has_senior', 'มีผู้สูงอายุ'
        GROUP = 'group', 'กลุ่ม (4+ คน)'
        MEN_ONLY = 'men_only', 'ผู้ชายล้วน'
        WOMEN_ONLY = 'women_only', 'ผู้หญิงล้วน'
        DEFAULT = 'default', 'ทั่วไป'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='upsell_rules')
    profile_type = models.CharField(max_length=20, choices=ProfileType.choices)
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='upsell_rules')
    reason = models.CharField(max_length=100, help_text='เหตุผลสั้นๆ เช่น "เมนูแนะนำสำหรับคู่"')
    priority = models.PositiveIntegerField(default=0, help_text='ยิ่งสูง ยิ่งแสดงก่อน')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'pos_menuupsellrule'
        ordering = ['-priority']

    def __str__(self):
        return f"{self.get_profile_type_display()} → {self.menu_item.name}"


# =============================================================================
# Transaction (Payment)
# =============================================================================

class Transaction(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'เงินสด'
        CARD = 'card', 'บัตรเครดิต/เดบิต'
        PROMPTPAY = 'promptpay', 'QR PromptPay'
        ROOM_CHARGE = 'room_charge', 'เซ็นห้อง'
        TRANSFER = 'transfer', 'โอนเงิน'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference = models.CharField(max_length=100, blank=True, help_text='เลขห้อง, ref number')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pos_transaction'
        ordering = ['-created_at']

    def __str__(self):
        return f"฿{self.amount} — {self.get_payment_method_display()} (Order #{self.order.order_number})"
