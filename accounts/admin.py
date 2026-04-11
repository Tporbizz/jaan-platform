from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import RestaurantBranch, Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RestaurantBranch)
class RestaurantBranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'phone', 'is_active']
    list_filter = ['tenant', 'is_active']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'tenant', 'restaurant_branch', 'is_active']
    list_filter = ['role', 'tenant', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Jaan', {'fields': ('tenant', 'role', 'restaurant_branch', 'phone', 'avatar')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Jaan', {'fields': ('tenant', 'role', 'restaurant_branch', 'phone')}),
    )
