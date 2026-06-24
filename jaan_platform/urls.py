from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import authenticate, login, logout
from django.db import models
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import include, path
from django.utils import timezone


def health_check(request):
    return JsonResponse({'status': 'ok'})


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def _today_kpis(tenant, today):
    """KPI ยอดขายวันนี้ + P&L เดือนนี้ — คำนวณด้วย aggregate (กัน N+1)"""
    from pos.models import Order
    from reports.models import MonthlyPL

    agg = Order.objects.filter(
        tenant=tenant, status='paid', opened_at__date=today,
    ).aggregate(
        revenue=models.Sum('total'),
        covers=models.Sum('guest_count'),
        count=models.Count('id'),
    )
    pl = MonthlyPL.objects.filter(tenant=tenant, month=today.month, year=today.year).first()
    return {
        'today_revenue': agg['revenue'] or 0,
        'today_order_count': agg['count'] or 0,
        'today_covers': agg['covers'] or 0,
        'pl': pl,
        'today': today,
    }


def dashboard_kpis(request):
    """Partial — แถบ KPI ยอดขายวันนี้ สำหรับ HTMX poll (อัปเดตสด)"""
    if not request.user.is_authenticated:
        return redirect('login')
    today = timezone.localdate()
    return render(request, 'includes/_dashboard_kpis.html', _today_kpis(request.user.tenant, today))


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    today = timezone.localdate()

    kpis = _today_kpis(tenant, today)
    today_revenue = kpis['today_revenue']
    today_order_count = kpis['today_order_count']
    today_covers = kpis['today_covers']
    pl = kpis['pl']

    # Expiry alerts
    from restaurant.models import LotBatch
    expiring = LotBatch.objects.filter(
        tenant=tenant, expiry_date__lte=today + timezone.timedelta(days=3),
        quantity__gt=0,
    ).select_related('item')[:5]

    # Low stock
    from restaurant.models import Item
    low_stock = Item.objects.filter(tenant=tenant, current_stock__lt=models.F('min_stock'))[:5]

    # Today's shifts
    from hr.models import ShiftSchedule
    today_shifts = ShiftSchedule.objects.filter(
        employee__tenant=tenant, date=today,
    ).select_related('employee')[:8]

    # Active events
    from events.models import EventSession
    active_events = EventSession.objects.filter(tenant=tenant, status='active')

    context = {
        'today_revenue': today_revenue,
        'today_order_count': today_order_count,
        'today_covers': today_covers,
        'pl': pl,
        'expiring': expiring,
        'low_stock': low_stock,
        'today_shifts': today_shifts,
        'active_events': active_events,
        'today': today,
    }
    return render(request, 'dashboard.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        error = 'Username/Email หรือ Password ไม่ถูกต้อง'
    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


urlpatterns = [
    path('', landing, name='landing'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/kpis/', dashboard_kpis, name='dashboard_kpis'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('stock/', include('restaurant.urls', namespace='restaurant')),
    path('procurement/', include(('restaurant.procurement_urls', 'procurement'), namespace='procurement')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('events/', include('events.urls', namespace='events')),
    path('hr/', include('hr.urls', namespace='hr')),
    path('hotel/', include('hotel_integration.urls', namespace='hotel_integration')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('settings/', include(('restaurant.settings_urls', 'settings'), namespace='settings')),
    path('ai/', include(('restaurant.ai_urls', 'ai'), namespace='ai')),
    path('api/accounts/', include('accounts.urls', namespace='accounts')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
