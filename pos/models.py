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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='tables', verbose_name='ร้าน')
    number = models.CharField('หมายเลขโต๊ะ', max_length=10)
    name = models.CharField('ชื่อ', max_length=50, blank=True, help_text='เช่น โต๊ะริมน้ำ, ห้อง VIP')
    capacity = models.PositiveIntegerField('ความจุ', default=4)
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.EMPTY)
    zone = models.CharField('โซน', max_length=50, blank=True, help_text='โซน เช่น ในร้าน, ริมน้ำ, ชั้น 2')
    grid_x = models.PositiveIntegerField('ตำแหน่ง X', default=0, help_text='ตำแหน่งบน floor plan')
    grid_y = models.PositiveIntegerField('ตำแหน่ง Y', default=0)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)
    sort_order = models.PositiveIntegerField('ลำดับ', default=0)

    class Meta:
        db_table = 'pos_table'
        verbose_name = 'โต๊ะ'
        verbose_name_plural = 'โต๊ะ'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='orders', verbose_name='ร้าน')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='โต๊ะ')
    order_number = models.CharField('เลขออเดอร์', max_length=20)
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.OPEN)

    # Guest info (สำหรับ upsell engine)
    guest_count = models.PositiveIntegerField('จำนวนลูกค้า', default=1)
    men_count = models.PositiveIntegerField('ผู้ชาย', default=0)
    women_count = models.PositiveIntegerField('ผู้หญิง', default=0)
    children_count = models.PositiveIntegerField('เด็ก', default=0)
    senior_count = models.PositiveIntegerField('ผู้สูงอายุ', default=0)

    subtotal = models.DecimalField('ยอดก่อนหัก', max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField('ส่วนลด', max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField('ค่าบริการ', max_digits=10, decimal_places=2, default=0)
    vat = models.DecimalField('VAT', max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField('ยอดรวม', max_digits=10, decimal_places=2, default=0)

    notes = models.TextField('หมายเหตุ', blank=True)
    opened_at = models.DateTimeField('เปิดเมื่อ', auto_now_add=True)
    closed_at = models.DateTimeField('ปิดเมื่อ', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='orders_created', verbose_name='สร้างโดย')

    # ระบบอัตโนมัติ: กันตัดสต็อกซ้ำเมื่อจ่ายเงินแล้ว
    stock_depleted = models.BooleanField('ตัดสต็อกแล้ว', default=False,
                                         help_text='ระบบตั้งให้อัตโนมัติเมื่อตัดวัตถุดิบตามสูตรแล้ว')

    class Meta:
        db_table = 'pos_order'
        verbose_name = 'ออเดอร์'
        verbose_name_plural = 'ออเดอร์'
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

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='ออเดอร์')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='order_items', verbose_name='เมนู')
    quantity = models.PositiveIntegerField('จำนวน', default=1)
    unit_price = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2)
    special_request = models.CharField('คำขอพิเศษ', max_length=200, blank=True)
    status = models.CharField('สถานะ', max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING)
    is_voided = models.BooleanField('ยกเลิกแล้ว', default=False)
    void_reason = models.CharField('เหตุผลยกเลิก', max_length=200, blank=True)
    cost_snapshot = models.DecimalField('ต้นทุนวัตถุดิบจริง', max_digits=10, decimal_places=2, default=0,
                                        help_text='ต้นทุนจริงที่ตัดจากสต็อก (FIFO) เมื่อขาย — ใช้คำนวณ Food Cost จริง')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)
    served_at = models.DateTimeField('เสิร์ฟเมื่อ', null=True, blank=True)

    class Meta:
        db_table = 'pos_orderitem'
        verbose_name = 'รายการออเดอร์'
        verbose_name_plural = 'รายการออเดอร์'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='kitchen_tickets', verbose_name='ร้าน')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='kitchen_tickets', verbose_name='ออเดอร์')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, verbose_name='โต๊ะ')
    ticket_number = models.CharField('เลข Ticket', max_length=20)
    status = models.CharField('สถานะ', max_length=20, choices=TicketStatus.choices, default=TicketStatus.PENDING)
    prepared_by = models.ForeignKey(
        'hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kitchen_tickets', verbose_name='ผู้รับผิดชอบ',
        help_text='เชฟ/คนครัวที่รับผิดชอบ',
    )
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)
    completed_at = models.DateTimeField('เสร็จเมื่อ', null=True, blank=True)
    notes = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        db_table = 'pos_kitchenticket'
        verbose_name = 'ใบสั่งครัว'
        verbose_name_plural = 'ใบสั่งครัว'
        ordering = ['-created_at']

    def __str__(self):
        return f"KT-{self.ticket_number} (โต๊ะ {self.table.number if self.table else 'N/A'})"


class KitchenTicketItem(models.Model):
    ticket = models.ForeignKey(KitchenTicket, on_delete=models.CASCADE, related_name='items', verbose_name='ใบสั่งครัว')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='ticket_items', verbose_name='รายการออเดอร์')
    quantity = models.PositiveIntegerField('จำนวน', default=1)
    special_request = models.CharField('คำขอพิเศษ', max_length=200, blank=True)
    is_done = models.BooleanField('ทำเสร็จแล้ว', default=False)

    class Meta:
        db_table = 'pos_kitchenticketitem'
        verbose_name = 'รายการใบสั่งครัว'
        verbose_name_plural = 'รายการใบสั่งครัว'

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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='upsell_rules', verbose_name='ร้าน')
    profile_type = models.CharField('ประเภทลูกค้า', max_length=20, choices=ProfileType.choices)
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='upsell_rules', verbose_name='เมนู')
    reason = models.CharField('เหตุผล', max_length=100, help_text='เหตุผลสั้นๆ เช่น "เมนูแนะนำสำหรับคู่"')
    priority = models.PositiveIntegerField('ลำดับความสำคัญ', default=0, help_text='ยิ่งสูง ยิ่งแสดงก่อน')
    is_active = models.BooleanField('เปิดใช้งาน', default=True)

    class Meta:
        db_table = 'pos_menuupsellrule'
        verbose_name = 'กฎ Upsell'
        verbose_name_plural = 'กฎ Upsell'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='transactions', verbose_name='ร้าน')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions', verbose_name='ออเดอร์')
    payment_method = models.CharField('วิธีชำระ', max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField('จำนวนเงิน', max_digits=10, decimal_places=2)
    received = models.DecimalField('รับมา', max_digits=10, decimal_places=2, default=0)
    change = models.DecimalField('ทอน', max_digits=10, decimal_places=2, default=0)
    reference = models.CharField('อ้างอิง', max_length=100, blank=True, help_text='เลขห้อง, ref number')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='ดำเนินการโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'pos_transaction'
        verbose_name = 'รายการชำระเงิน'
        verbose_name_plural = 'รายการชำระเงิน'
        ordering = ['-created_at']

    def __str__(self):
        return f"฿{self.amount} — {self.get_payment_method_display()} (Order #{self.order.order_number})"


# =============================================================================
# Sales Campaign — เป้าเชียร์ขายประจำวัน + ค่าคอมต่อจาน
# =============================================================================

class SalesCampaign(models.Model):
    """เป้าเชียร์ขายประจำวัน — ผู้จัดการเลือกเมนูกำไรดีให้ทีมดันยอด พร้อมตั้งค่าคอมต่อจาน"""

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='campaigns', verbose_name='ร้าน')
    date = models.DateField('วันที่')
    title = models.CharField('ชื่อแคมเปญ', max_length=120, default='เป้าเชียร์ขายวันนี้')
    note = models.TextField('โน้ตถึงทีม', blank=True, help_text='ข้อความกระตุ้นทีม เช่น เน้นเชียร์ของหวาน')
    is_active = models.BooleanField('เปิดใช้งาน', default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='ตั้งโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'pos_salescampaign'
        verbose_name = 'แคมเปญเชียร์ขาย'
        verbose_name_plural = 'แคมเปญเชียร์ขาย'
        ordering = ['-date']
        unique_together = ['tenant', 'date']

    def __str__(self):
        return f"{self.title} ({self.date})"


class CampaignItem(models.Model):
    """เมนูเป้าในแคมเปญ — เป้าจำนวนทีม + ค่าคอมต่อจานที่คนขายได้รับ"""

    campaign = models.ForeignKey(SalesCampaign, on_delete=models.CASCADE, related_name='items', verbose_name='แคมเปญ')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='campaign_items', verbose_name='เมนู')
    target_qty = models.PositiveIntegerField('เป้าทีม (จาน)', default=10, help_text='ทีมต้องขายรวมให้ได้กี่จานวันนี้')
    commission_per_dish = models.DecimalField('ค่าคอมต่อจาน', max_digits=8, decimal_places=2, default=0,
                                              help_text='เงินที่คนขายได้รับต่อการขาย 1 จาน')

    class Meta:
        db_table = 'pos_campaignitem'
        verbose_name = 'เมนูเป้า'
        verbose_name_plural = 'เมนูเป้า'
        unique_together = ['campaign', 'menu_item']

    def __str__(self):
        return f"{self.menu_item.name} — เป้า {self.target_qty} จาน (+฿{self.commission_per_dish}/จาน)"
