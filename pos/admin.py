from django.contrib import admin

from .models import (
    KitchenTicket, KitchenTicketItem, MenuUpsellRule,
    Order, OrderItem, Table, Transaction,
)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'capacity', 'status', 'zone', 'tenant']
    list_filter = ['tenant', 'status', 'zone']
    list_editable = ['status', 'capacity']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table', 'status', 'guest_count', 'subtotal', 'total', 'opened_at']
    list_filter = ['tenant', 'status']
    inlines = [OrderItemInline]


class KitchenTicketItemInline(admin.TabularInline):
    model = KitchenTicketItem
    extra = 0


@admin.register(KitchenTicket)
class KitchenTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'table', 'status', 'created_at']
    list_filter = ['tenant', 'status']
    inlines = [KitchenTicketItemInline]


@admin.register(MenuUpsellRule)
class MenuUpsellRuleAdmin(admin.ModelAdmin):
    list_display = ['profile_type', 'menu_item', 'reason', 'priority', 'is_active']
    list_filter = ['tenant', 'profile_type', 'is_active']
    list_editable = ['priority', 'is_active']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['order', 'payment_method', 'amount', 'received', 'change', 'created_at']
    list_filter = ['tenant', 'payment_method']
