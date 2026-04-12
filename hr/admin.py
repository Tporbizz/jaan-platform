from django.contrib import admin

from .models import Employee, ShiftSchedule


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'nickname', 'position', 'phone', 'is_active']
    list_filter = ['tenant', 'position', 'is_active']
    search_fields = ['first_name', 'last_name', 'nickname']


@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'shift_type']
    list_filter = ['shift_type', 'date']
