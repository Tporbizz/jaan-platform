"""
API ViewSets — read-only, แยกข้อมูลตามร้าน (tenant) อัตโนมัติ
Auth: JWT (ดู /api/accounts/token/) — ส่ง header Authorization: Bearer <token>
"""
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F, Sum, Count

from restaurant.models import Item, MenuItem
from reports.models import DailySalesRecord, MonthlyPL
from pos.models import Order
from . import serializers


class _TenantMixin:
    """กรองข้อมูลเฉพาะร้านของผู้ใช้ที่ล็อกอิน"""
    permission_classes = [IsAuthenticated]

    def get_tenant(self):
        return self.request.user.tenant


class ItemViewSet(_TenantMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ItemSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']

    def get_queryset(self):
        return (Item.objects.filter(tenant=self.get_tenant(), is_active=True)
                .select_related('category', 'unit', 'default_supplier').order_by('name'))


class MenuViewSet(_TenantMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.MenuSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'name_en']

    def get_queryset(self):
        return (MenuItem.objects.filter(tenant=self.get_tenant())
                .select_related('recipe').prefetch_related('recipe__ingredients__item')
                .order_by('menu_category', 'name'))


class DailySalesViewSet(_TenantMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.DailySalesSerializer

    def get_queryset(self):
        return DailySalesRecord.objects.filter(tenant=self.get_tenant()).order_by('-date')


class MonthlyPLViewSet(_TenantMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.MonthlyPLSerializer

    def get_queryset(self):
        return MonthlyPL.objects.filter(tenant=self.get_tenant()).order_by('-year', '-month')


class OrderViewSet(_TenantMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        qs = Order.objects.filter(tenant=self.get_tenant()).select_related('table').order_by('-opened_at')
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary(request):
    """สรุป KPI วันนี้ — endpoint เดียวสำหรับ dashboard ภายนอก"""
    tenant = request.user.tenant
    today = timezone.localdate()
    agg = Order.objects.filter(tenant=tenant, status='paid', opened_at__date=today).aggregate(
        revenue=Sum('total'), covers=Sum('guest_count'), orders=Count('id'))
    low_stock = Item.objects.filter(tenant=tenant, is_active=True, current_stock__lt=F('min_stock')).count()
    return Response({
        'date': today,
        'today_revenue': agg['revenue'] or 0,
        'today_orders': agg['orders'] or 0,
        'today_covers': agg['covers'] or 0,
        'low_stock_count': low_stock,
    })
