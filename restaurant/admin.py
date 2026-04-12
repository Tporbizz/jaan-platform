from django.contrib import admin

from .models import (
    Category, Item, KPITarget, LotBatch, MenuItem, POItem,
    PriceHistory, PurchaseOrder, Recipe, RecipeItem, StockCount,
    StockMovement, Subcategory, Supplier, Unit, WasteRecord,
)

# --- Thai Admin Site ---
admin.site.site_header = 'จาน — Restaurant OS'
admin.site.site_title = 'จาน Admin'
admin.site.index_title = 'จัดการข้อมูลทั้งหมด'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'sort_order']
    list_filter = ['tenant']


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'tenant']
    list_filter = ['tenant', 'category']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'tenant']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'is_active', 'tenant']
    list_filter = ['tenant', 'is_active']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'current_stock', 'min_stock', 'cost_per_unit', 'stock_status', 'tenant']
    list_filter = ['tenant', 'category', 'is_active']
    search_fields = ['name']


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['name', 'portions', 'tenant']
    inlines = [RecipeItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'menu_category', 'selling_price', 'food_cost_pct', 'is_available']
    list_filter = ['tenant', 'menu_category', 'is_available']


class POItemInline(admin.TabularInline):
    model = POItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'status', 'order_date', 'total_amount']
    list_filter = ['tenant', 'status', 'supplier']
    inlines = [POItemInline]


@admin.register(LotBatch)
class LotBatchAdmin(admin.ModelAdmin):
    list_display = ['item', 'lot_number', 'quantity', 'expiry_date', 'days_until_expiry', 'is_expired']
    list_filter = ['tenant']


@admin.register(WasteRecord)
class WasteRecordAdmin(admin.ModelAdmin):
    list_display = ['item', 'quantity', 'reason', 'cost_impact', 'waste_date']
    list_filter = ['tenant', 'reason']


@admin.register(KPITarget)
class KPITargetAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'food_cost_target_pct', 'labour_cost_target_pct', 'revenue_target']
    list_filter = ['tenant', 'year']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['item', 'old_price', 'new_price', 'change_pct', 'reason', 'created_at']
    list_filter = ['tenant', 'reason']
    readonly_fields = ['change_pct']


admin.site.register(StockMovement)
admin.site.register(StockCount)
admin.site.register(RecipeItem)
