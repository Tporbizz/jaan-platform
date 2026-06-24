from decimal import Decimal

from django.db.models import Sum, F, Count
from django.shortcuts import redirect, render
from django.utils import timezone

from pos.models import Order, Transaction
from restaurant.models import (
    Item, KPITarget, MenuItem, Recipe, StockMovement, WasteRecord,
)
from .models import ACUsageLog, DailySalesRecord, MonthlyPL


# =============================================================================
# Phase 5 — Food Cost Engine
# =============================================================================

def pricing_calculator(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant

    menu_items = MenuItem.objects.filter(
        tenant=tenant, is_available=True, recipe__isnull=False,
    ).select_related('recipe')

    items_data = []
    for mi in menu_items:
        cost = mi.recipe.calculate_cost() if mi.recipe else 0
        fc_pct = mi.food_cost_pct or 0
        gp = mi.gross_profit or 0

        # ABC classification
        if fc_pct and fc_pct <= 33:
            abc = 'star'
        elif fc_pct and fc_pct <= 38:
            abc = 'plow'
        elif fc_pct and fc_pct <= 45:
            abc = 'puzzle'
        else:
            abc = 'dog'

        items_data.append({
            'item': mi,
            'cost': cost,
            'fc_pct': fc_pct,
            'gp': gp,
            'abc': abc,
        })

    # Scenario table
    target_pcts = [25, 28, 30, 33, 35, 40]

    context = {
        'items_data': items_data,
        'target_pcts': target_pcts,
        'total_items': len(items_data),
        'high_fc_count': sum(1 for d in items_data if d['fc_pct'] and d['fc_pct'] > 35),
    }
    return render(request, 'reports/pricing_calculator.html', context)


def variance_report(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.localdate()

    # Current month
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    # Theoretical cost from POS orders this month
    paid_orders = Order.objects.filter(
        tenant=tenant, status='paid',
        opened_at__year=year, opened_at__month=month,
    )
    theoretical_cost = Decimal('0')
    for order in paid_orders:
        for oi in order.items.filter(is_voided=False):
            if oi.menu_item.recipe:
                theoretical_cost += oi.menu_item.recipe.calculate_cost() * oi.quantity

    # Actual cost = purchases this month
    purchases = StockMovement.objects.filter(
        tenant=tenant, movement_type='in',
        created_at__year=year, created_at__month=month,
    ).aggregate(total=Sum(F('quantity') * F('unit_cost')))['total'] or Decimal('0')

    # Waste
    waste = WasteRecord.objects.filter(
        tenant=tenant, waste_date__year=year, waste_date__month=month,
    ).aggregate(total=Sum('cost_impact'))['total'] or Decimal('0')

    variance = purchases - theoretical_cost
    variance_pct = (variance / theoretical_cost * 100) if theoretical_cost else 0

    # Revenue
    revenue = paid_orders.aggregate(total=Sum('total'))['total'] or Decimal('0')
    fc_actual_pct = (purchases / revenue * 100) if revenue else 0
    fc_theo_pct = (theoretical_cost / revenue * 100) if revenue else 0

    # KPI target
    kpi = KPITarget.objects.filter(tenant=tenant, month=month, year=year).first()

    context = {
        'month': month,
        'year': year,
        'revenue': revenue,
        'theoretical_cost': theoretical_cost,
        'actual_cost': purchases,
        'waste_cost': waste,
        'variance': variance,
        'variance_pct': variance_pct,
        'fc_actual_pct': fc_actual_pct,
        'fc_theo_pct': fc_theo_pct,
        'kpi': kpi,
    }
    return render(request, 'reports/variance_report.html', context)


# =============================================================================
# Phase 7 — P&L Dashboard
# =============================================================================

def pl_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.localdate()

    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))

    pl, created = MonthlyPL.objects.get_or_create(
        tenant=tenant, month=month, year=year,
    )

    # Auto-calculate from data
    paid_orders = Order.objects.filter(
        tenant=tenant, status='paid',
        opened_at__year=year, opened_at__month=month,
    )
    pl.dine_in_revenue = paid_orders.aggregate(total=Sum('total'))['total'] or 0

    # Event revenue
    from events.models import EventSession
    event_sessions = EventSession.objects.filter(
        tenant=tenant, date__year=year, date__month=month, status='closed',
    )
    pl.event_revenue = sum(s.total_revenue for s in event_sessions)

    pl.total_revenue = pl.dine_in_revenue + pl.beverage_revenue + pl.bf_revenue + pl.event_revenue

    # COGS
    purchases = StockMovement.objects.filter(
        tenant=tenant, movement_type='in',
        created_at__year=year, created_at__month=month,
    ).aggregate(total=Sum(F('quantity') * F('unit_cost')))['total'] or 0
    pl.food_cost_actual = purchases

    # Theoretical
    theo = Decimal('0')
    for order in paid_orders:
        for oi in order.items.filter(is_voided=False):
            if oi.menu_item.recipe:
                theo += oi.menu_item.recipe.calculate_cost() * oi.quantity
    pl.food_cost_theoretical = theo

    pl.waste_cost = WasteRecord.objects.filter(
        tenant=tenant, waste_date__year=year, waste_date__month=month,
    ).aggregate(total=Sum('cost_impact'))['total'] or 0

    # Labour
    from hr.models import PayrollRecord
    labour = PayrollRecord.objects.filter(
        employee__tenant=tenant, month=month, year=year,
    ).aggregate(total=Sum('net_pay'))['total'] or 0
    pl.labour_cost = labour

    # Electricity from Sensibo
    from reports.models import ACUsageLog
    ac_cost = ACUsageLog.objects.filter(
        tenant=tenant, timestamp__year=year, timestamp__month=month,
    ).aggregate(total=Sum('estimated_cost_thb'))['total'] or 0
    pl.electricity_cost = ac_cost

    pl.calculate()
    pl.save()

    kpi = KPITarget.objects.filter(tenant=tenant, month=month, year=year).first()

    context = {
        'pl': pl,
        'month': month,
        'year': year,
        'kpi': kpi,
    }
    return render(request, 'reports/pl_dashboard.html', context)


# =============================================================================
# Phase 8 — Sensibo Dashboard
# =============================================================================

def sensibo_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.localdate()

    today_logs = ACUsageLog.objects.filter(
        tenant=tenant, timestamp__date=today,
    )
    today_cost = today_logs.aggregate(total=Sum('estimated_cost_thb'))['total'] or 0

    month_logs = ACUsageLog.objects.filter(
        tenant=tenant, timestamp__year=today.year, timestamp__month=today.month,
    )
    month_cost = month_logs.aggregate(total=Sum('estimated_cost_thb'))['total'] or 0

    latest = today_logs.order_by('-timestamp').first()

    context = {
        'today_cost': today_cost,
        'month_cost': month_cost,
        'latest': latest,
        'today_logs': today_logs[:24],
    }
    return render(request, 'reports/sensibo_dashboard.html', context)
