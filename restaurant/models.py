from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# Base: Category, Unit, Supplier
# =============================================================================

class Category(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='categories', verbose_name='ร้าน')
    name = models.CharField('ชื่อ', max_length=100)
    description = models.TextField('รายละเอียด', blank=True)
    sort_order = models.PositiveIntegerField('ลำดับ', default=0)

    class Meta:
        db_table = 'restaurant_category'
        verbose_name = 'หมวดหมู่'
        verbose_name_plural = 'หมวดหมู่'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='subcategories', verbose_name='ร้าน')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name='หมวดหมู่')
    name = models.CharField('ชื่อ', max_length=100)

    class Meta:
        db_table = 'restaurant_subcategory'
        verbose_name = 'หมวดหมู่ย่อย'
        verbose_name_plural = 'หมวดหมู่ย่อย'

    def __str__(self):
        return f"{self.category.name} > {self.name}"


class Unit(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='units', verbose_name='ร้าน')
    name = models.CharField('ชื่อ', max_length=50)
    abbreviation = models.CharField('ตัวย่อ', max_length=10)

    class Meta:
        db_table = 'restaurant_unit'
        verbose_name = 'หน่วย'
        verbose_name_plural = 'หน่วย'

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Supplier(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='suppliers', verbose_name='ร้าน')
    name = models.CharField('ชื่อ', max_length=200)
    contact_person = models.CharField('ผู้ติดต่อ', max_length=100, blank=True)
    phone = models.CharField('โทรศัพท์', max_length=20, blank=True)
    email = models.EmailField('อีเมล', blank=True)
    line_id = models.CharField('Line ID', max_length=50, blank=True)
    address = models.TextField('ที่อยู่', blank=True)
    notes = models.TextField('หมายเหตุ', blank=True)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)

    class Meta:
        db_table = 'restaurant_supplier'
        verbose_name = 'ผู้จำหน่าย'
        verbose_name_plural = 'ผู้จำหน่าย'

    def __str__(self):
        return self.name


# =============================================================================
# Item (วัตถุดิบ)
# =============================================================================

class Item(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='items', verbose_name='ร้าน')
    code = models.CharField('รหัสวัตถุดิบ', max_length=30, blank=True, db_index=True,
                            help_text='รหัสอ้างอิง เช่น FF-0001 (จาก Market List)')
    name = models.CharField('ชื่อ', max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items', verbose_name='หมวดหมู่')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', verbose_name='หมวดหมู่ย่อย')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='items', verbose_name='หน่วย')
    default_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', verbose_name='ผู้จำหน่ายหลัก')

    current_stock = models.DecimalField('สต็อกปัจจุบัน', max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField('ขั้นต่ำ', max_digits=10, decimal_places=2, default=0)
    max_stock = models.DecimalField('สูงสุด', max_digits=10, decimal_places=2, default=0)
    cost_per_unit = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2, default=0)

    is_active = models.BooleanField('เปิดใช้งาน', default=True)
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)
    updated_at = models.DateTimeField('แก้ไขเมื่อ', auto_now=True)

    class Meta:
        db_table = 'restaurant_item'
        verbose_name = 'วัตถุดิบ'
        verbose_name_plural = 'วัตถุดิบ'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def stock_value(self):
        return self.current_stock * self.cost_per_unit

    @property
    def is_below_min(self):
        return self.current_stock < self.min_stock

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'out'
        if self.current_stock < self.min_stock:
            return 'low'
        if self.max_stock and self.current_stock > self.max_stock:
            return 'over'
        return 'ok'


# =============================================================================
# Stock Movement & Count
# =============================================================================

class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        IN = 'in', 'รับเข้า'
        OUT = 'out', 'เบิกออก'
        ADJUST = 'adjust', 'ปรับยอด'
        WASTE = 'waste', 'ทิ้ง/เสีย'
        TRANSFER = 'transfer', 'โอนย้าย'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='stock_movements', verbose_name='ร้าน')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movements', verbose_name='วัตถุดิบ')
    movement_type = models.CharField('ประเภท', max_length=10, choices=MovementType.choices)
    quantity = models.DecimalField('จำนวน', max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2, default=0)
    reference = models.CharField('อ้างอิง', max_length=200, blank=True)
    notes = models.TextField('หมายเหตุ', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='บันทึกโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'restaurant_stockmovement'
        verbose_name = 'การเคลื่อนไหวสต็อก'
        verbose_name_plural = 'การเคลื่อนไหวสต็อก'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.item.name} x{self.quantity}"


class StockCount(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='stock_counts', verbose_name='ร้าน')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='counts', verbose_name='วัตถุดิบ')
    counted_quantity = models.DecimalField('จำนวนนับได้', max_digits=10, decimal_places=2)
    system_quantity = models.DecimalField('จำนวนในระบบ', max_digits=10, decimal_places=2)
    variance = models.DecimalField('ส่วนต่าง', max_digits=10, decimal_places=2, default=0)
    count_date = models.DateField('วันที่นับ')
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='นับโดย')
    notes = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        db_table = 'restaurant_stockcount'
        verbose_name = 'การนับสต็อก'
        verbose_name_plural = 'การนับสต็อก'
        ordering = ['-count_date']

    def save(self, *args, **kwargs):
        self.variance = self.counted_quantity - self.system_quantity
        super().save(*args, **kwargs)


# =============================================================================
# Recipe & MenuItem
# =============================================================================

class Recipe(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='recipes', verbose_name='ร้าน')
    name = models.CharField('ชื่อ', max_length=200)
    description = models.TextField('รายละเอียด', blank=True)
    portions = models.PositiveIntegerField('จำนวนจาน', default=1, help_text='จำนวนจานที่ได้จาก recipe นี้')
    preparation_notes = models.TextField('วิธีเตรียม', blank=True)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)

    class Meta:
        db_table = 'restaurant_recipe'
        verbose_name = 'สูตรอาหาร'
        verbose_name_plural = 'สูตรอาหาร'

    def __str__(self):
        return self.name

    def calculate_cost(self):
        total = sum(ri.get_cost() for ri in self.ingredients.all())
        return total / self.portions if self.portions else total


class RecipeItem(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients', verbose_name='สูตร')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='recipe_uses', verbose_name='วัตถุดิบ')
    quantity = models.DecimalField('จำนวน', max_digits=10, decimal_places=3)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name='หน่วย')
    notes = models.CharField('หมายเหตุ', max_length=200, blank=True)

    class Meta:
        db_table = 'restaurant_recipeitem'
        verbose_name = 'ส่วนผสม'
        verbose_name_plural = 'ส่วนผสม'

    def __str__(self):
        return f"{self.recipe.name} — {self.item.name} x{self.quantity}"

    def get_cost(self):
        return self.quantity * self.item.cost_per_unit


class MenuItem(models.Model):
    class MenuCategory(models.TextChoices):
        SOUP = 'soup', 'แกง'
        STIR_FRY = 'stir_fry', 'ผัด'
        BOIL = 'boil', 'ต้ม'
        DEEP_FRY = 'deep_fry', 'ทอด'
        CHILI_PASTE = 'chili_paste', 'ชุดน้ำพริก'
        SALAD = 'salad', 'ยำ'
        STEAK = 'steak', 'สเต๊ก'
        SINGLE_DISH = 'single_dish', 'อาหารจานเดียว'
        PASTA = 'pasta', 'พาสต้า'
        SNACK = 'snack', 'อาหารทานเล่น'
        DESSERT = 'dessert', 'ของหวาน'
        COCKTAIL = 'cocktail', 'Cocktails'
        MOCKTAIL = 'mocktail', 'Mocktails'
        SMOOTHIE = 'smoothie', 'Smoothie / Shake'
        COFFEE = 'coffee', 'Coffee & Tea'
        BEER = 'beer', 'Beer'
        SOFT_DRINK = 'soft_drink', 'Soft Drink'
        SET_MENU = 'set_menu', 'ชุดเซ็ท'

    class PrepStation(models.TextChoices):
        KITCHEN = 'kitchen', 'ครัว'
        BAR = 'bar', 'บาร์/เครื่องดื่ม'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='menu_items', verbose_name='ร้าน')
    name = models.CharField('ชื่อ', max_length=200)
    name_en = models.CharField('ชื่อภาษาอังกฤษ', max_length=200, blank=True)
    menu_category = models.CharField('หมวดเมนู', max_length=20, choices=MenuCategory.choices, default=MenuCategory.STIR_FRY)
    prep_station = models.CharField('สถานีเตรียม', max_length=10, choices=PrepStation.choices, default=PrepStation.KITCHEN,
                                    help_text='ครัว = ส่ง KDS, บาร์ = FB ทำเอง ไม่ส่งครัว')
    prep_time_minutes = models.PositiveIntegerField('เวลาเตรียม (นาที)', default=10, help_text='เวลาเตรียม (นาที)')
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_items', verbose_name='สูตร')
    selling_price = models.DecimalField('ราคาขาย', max_digits=10, decimal_places=2)
    image = models.ImageField('รูปภาพ', upload_to='menu/', blank=True)
    is_available = models.BooleanField('พร้อมขาย', default=True)
    sort_order = models.PositiveIntegerField('ลำดับ', default=0)

    class Meta:
        db_table = 'restaurant_menuitem'
        verbose_name = 'เมนู'
        verbose_name_plural = 'เมนู'
        ordering = ['menu_category', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name} (฿{self.selling_price})"

    @property
    def food_cost_pct(self):
        if not self.recipe or not self.selling_price:
            return None
        cost = self.recipe.calculate_cost()
        return round((cost / self.selling_price) * 100, 1)

    @property
    def gross_profit(self):
        if not self.recipe:
            return None
        return self.selling_price - self.recipe.calculate_cost()


# =============================================================================
# Purchase Order
# =============================================================================

class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'ร่าง'
        SENT = 'sent', 'ส่งแล้ว'
        PARTIAL = 'partial', 'รับบางส่วน'
        RECEIVED = 'received', 'รับครบ'
        CANCELLED = 'cancelled', 'ยกเลิก'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='purchase_orders', verbose_name='ร้าน')
    po_number = models.CharField('เลข PO', max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name='ผู้จำหน่าย')
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField('วันสั่ง', default=timezone.now)
    expected_date = models.DateField('วันที่คาดรับ', null=True, blank=True)
    received_date = models.DateField('วันที่รับจริง', null=True, blank=True)
    notes = models.TextField('หมายเหตุ', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='สร้างโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'restaurant_purchaseorder'
        verbose_name = 'ใบสั่งซื้อ'
        verbose_name_plural = 'ใบสั่งซื้อ'
        ordering = ['-order_date']

    def __str__(self):
        return f"PO-{self.po_number} ({self.supplier.name})"

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.items.all())


class POItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name='ใบสั่งซื้อ')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='po_items', verbose_name='วัตถุดิบ')
    quantity = models.DecimalField('จำนวน', max_digits=10, decimal_places=2)
    unit_price = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField('จำนวนที่รับแล้ว', max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'restaurant_poitem'
        verbose_name = 'รายการสั่งซื้อ'
        verbose_name_plural = 'รายการสั่งซื้อ'

    def __str__(self):
        return f"{self.item.name} x{self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


# =============================================================================
# Phase 1.1 — New Models: LotBatch, WasteRecord, KPITarget
# =============================================================================

class LotBatch(models.Model):
    """Lot tracking สำหรับ FIFO + expiry management"""
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='lot_batches', verbose_name='ร้าน')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='lots', verbose_name='วัตถุดิบ')
    lot_number = models.CharField('เลข Lot', max_length=50, blank=True)
    received_date = models.DateField('วันที่รับ', default=timezone.now)
    expiry_date = models.DateField('วันหมดอายุ', null=True, blank=True)
    quantity = models.DecimalField('จำนวน', max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField('ราคาต่อหน่วย', max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ผู้จำหน่าย')
    notes = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        db_table = 'restaurant_lotbatch'
        verbose_name = 'ล็อตสินค้า'
        verbose_name_plural = 'ล็อตสินค้า'
        ordering = ['expiry_date', 'received_date']

    def __str__(self):
        return f"{self.item.name} — Lot {self.lot_number or 'N/A'}"

    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.localdate()).days

    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.localdate()


class WasteRecord(models.Model):
    class WasteReason(models.TextChoices):
        EXPIRED = 'expired', 'หมดอายุ'
        OVER_PREP = 'over_prep', 'เตรียมเกิน'
        DROPPED = 'dropped', 'ตกหล่น'
        SPOILED = 'spoiled', 'เน่าเสีย'
        OTHER = 'other', 'อื่นๆ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='waste_records', verbose_name='ร้าน')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='waste_records', verbose_name='วัตถุดิบ')
    quantity = models.DecimalField('จำนวน', max_digits=10, decimal_places=2)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name='หน่วย')
    waste_date = models.DateField('วันที่บันทึก', default=timezone.now)
    reason = models.CharField('สาเหตุ', max_length=20, choices=WasteReason.choices)
    cost_impact = models.DecimalField('มูลค่าความเสียหาย', max_digits=10, decimal_places=2, default=0)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='บันทึกโดย')
    notes = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        db_table = 'restaurant_wasterecord'
        verbose_name = 'บันทึกของเสีย'
        verbose_name_plural = 'บันทึกของเสีย'
        ordering = ['-waste_date']

    def __str__(self):
        return f"Waste: {self.item.name} x{self.quantity} ({self.get_reason_display()})"

    def save(self, *args, **kwargs):
        self.cost_impact = self.quantity * self.item.cost_per_unit
        super().save(*args, **kwargs)


class KPITarget(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='kpi_targets', verbose_name='ร้าน')
    month = models.PositiveIntegerField('เดือน')
    year = models.PositiveIntegerField('ปี')
    food_cost_target_pct = models.DecimalField('เป้า Food Cost (%)', max_digits=5, decimal_places=2, default=33)
    labour_cost_target_pct = models.DecimalField('เป้า Labour Cost (%)', max_digits=5, decimal_places=2, default=30)
    revenue_target = models.DecimalField('เป้ารายได้', max_digits=12, decimal_places=2, default=0)
    waste_budget = models.DecimalField('งบของเสีย', max_digits=10, decimal_places=2, default=0)
    prime_cost_target = models.DecimalField('เป้า Prime Cost (%)', max_digits=5, decimal_places=2, default=63)

    class Meta:
        db_table = 'restaurant_kpitarget'
        verbose_name = 'เป้าหมาย KPI'
        verbose_name_plural = 'เป้าหมาย KPI'
        unique_together = ['tenant', 'month', 'year']

    def __str__(self):
        return f"KPI {self.month}/{self.year} — FC {self.food_cost_target_pct}%"


# =============================================================================
# Phase 2 — PriceHistory
# =============================================================================

class PriceHistory(models.Model):
    class ChangeReason(models.TextChoices):
        MARKET = 'market', 'ราคาตลาด'
        SEASONAL = 'seasonal', 'ตามฤดูกาล'
        SUPPLIER = 'supplier', 'เปลี่ยน supplier'
        WAR = 'war', 'สงคราม/วิกฤต'
        OTHER = 'other', 'อื่นๆ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='price_histories', verbose_name='ร้าน')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_histories', verbose_name='วัตถุดิบ')
    old_price = models.DecimalField('ราคาเดิม', max_digits=10, decimal_places=2)
    new_price = models.DecimalField('ราคาใหม่', max_digits=10, decimal_places=2)
    change_pct = models.DecimalField('% เปลี่ยนแปลง', max_digits=6, decimal_places=2, default=0)
    reason = models.CharField('สาเหตุ', max_length=20, choices=ChangeReason.choices, default=ChangeReason.MARKET)
    notes = models.TextField('หมายเหตุ', blank=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ใบสั่งซื้อ')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='บันทึกโดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'restaurant_pricehistory'
        verbose_name = 'ประวัติราคา'
        verbose_name_plural = 'ประวัติราคา'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item.name}: ฿{self.old_price} → ฿{self.new_price} ({self.change_pct:+.1f}%)"

    def save(self, *args, **kwargs):
        if self.old_price:
            self.change_pct = ((self.new_price - self.old_price) / self.old_price) * 100
        super().save(*args, **kwargs)
