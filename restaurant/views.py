from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Item, LotBatch, WasteRecord, KPITarget, MenuItem, PurchaseOrder


def stock_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    today = timezone.now().date()

    if not tenant:
        return render(request, 'restaurant/stock_dashboard.html', {'no_tenant': True})

    # Items
    items = Item.objects.filter(tenant=tenant, is_active=True)
    total_items = items.count()
    below_min = items.filter(current_stock__lt=F('min_stock')).order_by('current_stock')
    out_of_stock = items.filter(current_stock__lte=0)

    # Stock value
    total_stock_value = Decimal('0')
    for item in items:
        total_stock_value += item.stock_value

    # Expiring lots
    expiring_3d = LotBatch.objects.filter(
        tenant=tenant, expiry_date__isnull=False,
        expiry_date__lte=today + timezone.timedelta(days=3),
        expiry_date__gte=today, quantity__gt=0,
    )
    expiring_7d = LotBatch.objects.filter(
        tenant=tenant, expiry_date__isnull=False,
        expiry_date__lte=today + timezone.timedelta(days=7),
        expiry_date__gt=today + timezone.timedelta(days=3),
        quantity__gt=0,
    )
    expired = LotBatch.objects.filter(
        tenant=tenant, expiry_date__isnull=False,
        expiry_date__lt=today, quantity__gt=0,
    )

    # Waste this month
    waste_this_month = WasteRecord.objects.filter(
        tenant=tenant,
        waste_date__year=today.year,
        waste_date__month=today.month,
    ).aggregate(
        total_cost=Sum('cost_impact'),
        total_count=Count('id'),
    )

    # Menu items
    menu_items = MenuItem.objects.filter(tenant=tenant, is_available=True)

    # Pending POs
    pending_pos = PurchaseOrder.objects.filter(
        tenant=tenant, status__in=['draft', 'sent'],
    )

    context = {
        'total_items': total_items,
        'below_min': below_min,
        'below_min_count': below_min.count(),
        'out_of_stock': out_of_stock.count(),
        'total_stock_value': total_stock_value,
        'expiring_3d': expiring_3d,
        'expiring_3d_count': expiring_3d.count(),
        'expiring_7d': expiring_7d,
        'expiring_7d_count': expiring_7d.count(),
        'expired': expired,
        'expired_count': expired.count(),
        'waste_cost': waste_this_month['total_cost'] or 0,
        'waste_count': waste_this_month['total_count'] or 0,
        'menu_items': menu_items,
        'menu_count': menu_items.count(),
        'pending_pos': pending_pos,
        'pending_po_count': pending_pos.count(),
        'items': items[:20],
    }
    return render(request, 'restaurant/stock_dashboard.html', context)
