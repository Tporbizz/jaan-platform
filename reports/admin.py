from django.contrib import admin

from .models import ACUsageLog, DailySalesRecord, MonthlyPL


@admin.register(DailySalesRecord)
class DailySalesAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_revenue', 'total_covers', 'avg_check', 'food_cost_actual']
    list_filter = ['tenant']


@admin.register(MonthlyPL)
class MonthlyPLAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'total_revenue', 'gross_profit', 'net_profit',
                    'food_cost_pct', 'labour_cost_pct', 'prime_cost_pct']
    list_filter = ['tenant', 'year']


@admin.register(ACUsageLog)
class ACUsageLogAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'timestamp', 'power_watts', 'temperature', 'ac_on', 'estimated_cost_thb']
    list_filter = ['tenant', 'device_id']
