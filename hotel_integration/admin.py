from django.contrib import admin

from .models import BFSettlement, GuestList, HotelConfig, RoomCharge


@admin.register(HotelConfig)
class HotelConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'pms_type', 'sync_method', 'is_active']


@admin.register(GuestList)
class GuestListAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'guest_name', 'checkout_date', 'package_type', 'bf_included']
    list_filter = ['tenant', 'package_type']
    search_fields = ['room_number', 'guest_name']


@admin.register(RoomCharge)
class RoomChargeAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'guest_name', 'amount', 'status', 'created_at']
    list_filter = ['tenant', 'status']


@admin.register(BFSettlement)
class BFSettlementAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_covers', 'bb_covers', 'total_amount', 'approved']
    list_filter = ['tenant', 'approved']
