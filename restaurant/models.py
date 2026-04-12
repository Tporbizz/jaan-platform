from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# Base: Category, Unit, Supplier
# =============================================================================

class Category(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'restaurant_category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='subcategories')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'restaurant_subcategory'
        verbose_name_plural = 'Subcategories'

    def __str__(self):
        return f"{self.category.name} > {self.name}"


class Unit(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10)

    class Meta:
        db_table = 'restaurant_unit'

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Supplier(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    line_id = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'restaurant_supplier'

    def __str__(self):
        return self.name


# =============================================================================
# Item (วัตถุดิบ)
# =============================================================================

class Item(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='items')
    default_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')

    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurant_item'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='stock_movements')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurant_stockmovement'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.item.name} x{self.quantity}"


class StockCount(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='stock_counts')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='counts')
    counted_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    system_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    variance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    count_date = models.DateField()
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'restaurant_stockcount'
        ordering = ['-count_date']

    def save(self, *args, **kwargs):
        self.variance = self.counted_quantity - self.system_quantity
        super().save(*args, **kwargs)


# =============================================================================
# Recipe & MenuItem
# =============================================================================

class Recipe(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='recipes')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    portions = models.PositiveIntegerField(default=1, help_text='จำนวนจานที่ได้จาก recipe นี้')
    preparation_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'restaurant_recipe'

    def __str__(self):
        return self.name

    def calculate_cost(self):
        total = sum(ri.get_cost() for ri in self.ingredients.all())
        return total / self.portions if self.portions else total


class RecipeItem(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='recipe_uses')
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'restaurant_recipeitem'

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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    menu_category = models.CharField(max_length=20, choices=MenuCategory.choices, default=MenuCategory.STIR_FRY)
    prep_station = models.CharField(max_length=10, choices=PrepStation.choices, default=PrepStation.KITCHEN,
                                    help_text='ครัว = ส่ง KDS, บาร์ = FB ทำเอง ไม่ส่งครัว')
    prep_time_minutes = models.PositiveIntegerField(default=10, help_text='เวลาเตรียม (นาที)')
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_items')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu/', blank=True)
    is_available = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'restaurant_menuitem'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='purchase_orders')
    po_number = models.CharField(max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurant_purchaseorder'
        ordering = ['-order_date']

    def __str__(self):
        return f"PO-{self.po_number} ({self.supplier.name})"

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.items.all())


class POItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='po_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'restaurant_poitem'

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
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='lot_batches')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=50, blank=True)
    received_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'restaurant_lotbatch'
        verbose_name_plural = 'Lot batches'
        ordering = ['expiry_date', 'received_date']

    def __str__(self):
        return f"{self.item.name} — Lot {self.lot_number or 'N/A'}"

    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()


class WasteRecord(models.Model):
    class WasteReason(models.TextChoices):
        EXPIRED = 'expired', 'หมดอายุ'
        OVER_PREP = 'over_prep', 'เตรียมเกิน'
        DROPPED = 'dropped', 'ตกหล่น'
        SPOILED = 'spoiled', 'เน่าเสีย'
        OTHER = 'other', 'อื่นๆ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='waste_records')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='waste_records')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    waste_date = models.DateField(default=timezone.now)
    reason = models.CharField(max_length=20, choices=WasteReason.choices)
    cost_impact = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'restaurant_wasterecord'
        ordering = ['-waste_date']

    def __str__(self):
        return f"Waste: {self.item.name} x{self.quantity} ({self.get_reason_display()})"

    def save(self, *args, **kwargs):
        self.cost_impact = self.quantity * self.item.cost_per_unit
        super().save(*args, **kwargs)


class KPITarget(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='kpi_targets')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    food_cost_target_pct = models.DecimalField(max_digits=5, decimal_places=2, default=33)
    labour_cost_target_pct = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    revenue_target = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    waste_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prime_cost_target = models.DecimalField(max_digits=5, decimal_places=2, default=63)

    class Meta:
        db_table = 'restaurant_kpitarget'
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

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='price_histories')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_histories')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    change_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reason = models.CharField(max_length=20, choices=ChangeReason.choices, default=ChangeReason.MARKET)
    notes = models.TextField(blank=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurant_pricehistory'
        verbose_name_plural = 'Price histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item.name}: ฿{self.old_price} → ฿{self.new_price} ({self.change_pct:+.1f}%)"

    def save(self, *args, **kwargs):
        if self.old_price:
            self.change_pct = ((self.new_price - self.old_price) / self.old_price) * 100
        super().save(*args, **kwargs)
