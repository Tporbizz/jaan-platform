from django.contrib import admin

from .models import AuditLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'level', 'category', 'is_read', 'created_at')
    list_filter = ('level', 'category', 'is_read')
    search_fields = ('title', 'message')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'tenant', 'summary', 'created_at')
    list_filter = ('action',)
    search_fields = ('action', 'summary', 'object_id')
