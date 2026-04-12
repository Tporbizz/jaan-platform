from django.contrib import admin

from .models import EventOrder, EventOrderItem, EventSession


class EventOrderItemInline(admin.TabularInline):
    model = EventOrderItem
    extra = 0


@admin.register(EventSession)
class EventSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'location', 'status', 'total_orders', 'total_revenue']
    list_filter = ['tenant', 'status']
    readonly_fields = ['session_token']


@admin.register(EventOrder)
class EventOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'session', 'status', 'total', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method']
    inlines = [EventOrderItemInline]
