import json
from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import require_kitchen, require_pos
from restaurant.models import KPITarget, MenuItem
from .models import (
    KitchenTicket, KitchenTicketItem, MenuUpsellRule,
    Order, OrderItem, Table, Transaction,
)


# =============================================================================
# POS Dashboard — USP/STP, Sales Targets, Top Sellers
# =============================================================================

@require_pos
def pos_dashboard(request):

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'pos/pos_dashboard.html', {'no_tenant': True})

    today = timezone.now().date()

    # --- Today's sales ---
    today_orders = Order.objects.filter(tenant=tenant, status='paid', opened_at__date=today)
    today_revenue = sum(o.total for o in today_orders)
    today_count = today_orders.count()
    today_covers = sum(o.guest_count for o in today_orders)
    avg_check = today_revenue / today_covers if today_covers else 0

    # --- Monthly sales ---
    month_orders = Order.objects.filter(
        tenant=tenant, status='paid',
        opened_at__year=today.year, opened_at__month=today.month,
    )
    month_revenue = sum(o.total for o in month_orders)
    month_count = month_orders.count()
    month_covers = sum(o.guest_count for o in month_orders)

    # --- KPI targets ---
    kpi = KPITarget.objects.filter(tenant=tenant, month=today.month, year=today.year).first()
    revenue_target = kpi.revenue_target if kpi else Decimal('0')
    daily_target = revenue_target / 30 if revenue_target else Decimal('0')
    target_pct = (today_revenue / daily_target * 100) if daily_target else 0

    # --- Top sellers (this month) ---
    top_sellers = OrderItem.objects.filter(
        order__tenant=tenant, order__status='paid',
        order__opened_at__year=today.year, order__opened_at__month=today.month,
        is_voided=False,
    ).values('menu_item__name', 'menu_item__selling_price').annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price')),
    ).order_by('-total_qty')[:10]

    # --- Customer segments (STP analysis) ---
    segment_data = []
    for order in month_orders:
        if order.men_count == 1 and order.women_count == 1 and order.guest_count == 2:
            segment_data.append('couple')
        elif order.children_count > 0:
            segment_data.append('family')
        elif order.guest_count >= 4:
            segment_data.append('group')
        elif order.senior_count > 0:
            segment_data.append('senior')
        else:
            segment_data.append('general')

    segments = {}
    for s in segment_data:
        segments[s] = segments.get(s, 0) + 1

    segment_labels = {
        'couple': 'คู่รัก',
        'family': 'ครอบครัว',
        'group': 'กลุ่มเพื่อน (4+)',
        'senior': 'ผู้สูงอายุ',
        'general': 'ทั่วไป',
    }
    segment_list = [
        {'key': k, 'label': segment_labels.get(k, k), 'count': v,
         'pct': round(v / max(len(segment_data), 1) * 100)}
        for k, v in sorted(segments.items(), key=lambda x: -x[1])
    ]

    # --- High margin menus (push recommendations) ---
    high_margin = MenuItem.objects.filter(
        tenant=tenant, is_available=True, recipe__isnull=False,
    ).select_related('recipe')
    push_menus = []
    for m in high_margin:
        fc = m.food_cost_pct
        gp = m.gross_profit
        if fc and gp and fc <= 35:
            push_menus.append({
                'name': m.name,
                'price': m.selling_price,
                'fc_pct': fc,
                'gross_profit': gp,
            })
    push_menus.sort(key=lambda x: -x['gross_profit'])
    push_menus = push_menus[:5]

    # --- Active tables ---
    tables = Table.objects.filter(tenant=tenant, is_active=True)
    occupied = tables.filter(status='occupied').count()
    total_tables = tables.count()

    context = {
        'today_revenue': today_revenue,
        'today_count': today_count,
        'today_covers': today_covers,
        'avg_check': avg_check,
        'month_revenue': month_revenue,
        'month_count': month_count,
        'month_covers': month_covers,
        'revenue_target': revenue_target,
        'daily_target': daily_target,
        'target_pct': target_pct,
        'top_sellers': top_sellers,
        'segment_list': segment_list,
        'push_menus': push_menus,
        'occupied': occupied,
        'total_tables': total_tables,
        'today': today,
        'kpi': kpi,
    }
    return render(request, 'pos/pos_dashboard.html', context)


# =============================================================================
# Table Map
# =============================================================================

@require_pos
def table_map(request):

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'pos/table_map.html', {'no_tenant': True})

    tables = Table.objects.filter(tenant=tenant, is_active=True)

    tables_data = []
    for table in tables:
        active_order = Order.objects.filter(
            table=table, status__in=['open', 'sent', 'served', 'bill'],
        ).first()

        tables_data.append({
            'table': table,
            'order': active_order,
            'total': active_order.subtotal if active_order else 0,
            'guests': active_order.guest_count if active_order else 0,
            'duration': active_order.duration_minutes if active_order else 0,
        })

    context = {
        'tables_data': tables_data,
        'total_tables': tables.count(),
        'occupied': tables.filter(status='occupied').count(),
        'empty': tables.filter(status='empty').count(),
    }
    return render(request, 'pos/table_map.html', context)


# =============================================================================
# Open Table (สร้าง Order ใหม่)
# =============================================================================

@require_POST
def open_table(request, table_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    table = get_object_or_404(Table, id=table_id, tenant=tenant)

    # Check if table already has an active order
    active = Order.objects.filter(
        table=table, status__in=['open', 'sent', 'served', 'bill'],
    ).first()
    if active:
        return JsonResponse({'order_id': active.id, 'existing': True})

    guest_count = int(request.POST.get('guest_count', 1))
    men = int(request.POST.get('men_count', 0))
    women = int(request.POST.get('women_count', 0))
    children = int(request.POST.get('children_count', 0))
    senior = int(request.POST.get('senior_count', 0))

    # Generate order number
    today = timezone.now()
    daily_count = Order.objects.filter(
        tenant=tenant, opened_at__date=today.date(),
    ).count() + 1
    order_number = f"{today.strftime('%y%m%d')}-{daily_count:03d}"

    order = Order.objects.create(
        tenant=tenant,
        table=table,
        order_number=order_number,
        guest_count=guest_count,
        men_count=men,
        women_count=women,
        children_count=children,
        senior_count=senior,
        created_by=request.user,
    )

    table.status = 'occupied'
    table.save()

    return JsonResponse({'order_id': order.id, 'order_number': order_number})


# =============================================================================
# Order View (เพิ่มเมนู, ดู cart)
# =============================================================================

def order_view(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    # Menu items grouped by category
    menu_items = MenuItem.objects.filter(
        tenant=tenant, is_available=True,
    ).select_related('recipe').order_by('menu_category', 'sort_order', 'name')

    menu_by_cat = {}
    for item in menu_items:
        cat = item.get_menu_category_display()
        if cat not in menu_by_cat:
            menu_by_cat[cat] = []
        menu_by_cat[cat].append(item)

    # Order items
    order_items = order.items.filter(is_voided=False).select_related('menu_item')

    # Upsell suggestions
    suggestions = get_upsell_suggestions(tenant, order)

    has_pending = order_items.filter(status='pending').exists()

    context = {
        'order': order,
        'order_items': order_items,
        'menu_by_cat': menu_by_cat,
        'suggestions': suggestions,
        'categories': MenuItem.MenuCategory.choices,
        'has_pending': has_pending,
    }
    return render(request, 'pos/order_view.html', context)


# =============================================================================
# Order API (AJAX)
# =============================================================================

@require_POST
def add_item(request, order_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    data = json.loads(request.body)
    menu_item_id = data.get('menu_item_id')
    quantity = int(data.get('quantity', 1))
    special_request = data.get('special_request', '')

    menu_item = get_object_or_404(MenuItem, id=menu_item_id, tenant=tenant)

    # Check if same item already in order (merge)
    existing = order.items.filter(
        menu_item=menu_item, is_voided=False, status='pending', special_request=special_request,
    ).first()

    if existing:
        existing.quantity += quantity
        existing.save()
    else:
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            unit_price=menu_item.selling_price,
            special_request=special_request,
        )

    order.recalculate()

    return JsonResponse({
        'ok': True,
        'subtotal': str(order.subtotal),
        'total': str(order.total),
        'item_count': order.items.filter(is_voided=False).count(),
    })


@require_POST
def add_custom_item(request, order_id):
    """เพิ่มเมนูพิมพ์เอง (ไม่มีใน MenuItem) — สำหรับกรณีเร่งด่วน"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    data = json.loads(request.body)
    name = data.get('name', '').strip()
    price = Decimal(str(data.get('price', 0)))
    quantity = int(data.get('quantity', 1))

    if not name or price <= 0:
        return JsonResponse({'error': 'ต้องใส่ชื่อและราคา'}, status=400)

    # Find or create a "custom" MenuItem for this tenant
    custom_item, _ = MenuItem.objects.get_or_create(
        tenant=tenant,
        name=name,
        defaults={
            'selling_price': price,
            'menu_category': 'stir_fry',
            'prep_station': 'kitchen',
            'prep_time_minutes': 10,
            'is_available': True,
        },
    )
    # Update price if it differs (custom items may have varying prices)
    if custom_item.selling_price != price:
        custom_item.selling_price = price
        custom_item.save(update_fields=['selling_price'])

    OrderItem.objects.create(
        order=order,
        menu_item=custom_item,
        quantity=quantity,
        unit_price=price,
        special_request='[เมนูพิเศษ]',
    )

    order.recalculate()

    return JsonResponse({
        'ok': True,
        'subtotal': str(order.subtotal),
        'total': str(order.total),
    })


@require_POST
def void_item(request, order_id, item_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    data = json.loads(request.body)
    reason = data.get('reason', '')

    item = get_object_or_404(OrderItem, id=item_id, order=order)
    item.is_voided = True
    item.void_reason = reason
    item.status = 'voided'
    item.save()

    order.recalculate()

    return JsonResponse({'ok': True, 'subtotal': str(order.subtotal), 'total': str(order.total)})


@require_POST
def send_to_kitchen(request, order_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    # Get pending items
    pending_items = order.items.filter(
        status='pending', is_voided=False,
    ).select_related('menu_item')
    if not pending_items.exists():
        return JsonResponse({'error': 'No pending items'}, status=400)

    # Split: kitchen items vs bar items (beverages skip kitchen)
    kitchen_items = []
    bar_items = []
    for item in pending_items:
        if item.menu_item.prep_station == 'bar':
            bar_items.append(item)
        else:
            kitchen_items.append(item)

    # Bar items → mark ready immediately (FB ทำเอง)
    for item in bar_items:
        item.status = 'ready'
        item.save()

    # Kitchen items → create KitchenTicket
    ticket_number = None
    if kitchen_items:
        daily_count = KitchenTicket.objects.filter(
            tenant=tenant, created_at__date=timezone.now().date(),
        ).count() + 1
        ticket_number = f"KT-{timezone.now().strftime('%H%M')}-{daily_count:03d}"

        ticket = KitchenTicket.objects.create(
            tenant=tenant,
            order=order,
            table=order.table,
            ticket_number=ticket_number,
        )

        for item in kitchen_items:
            KitchenTicketItem.objects.create(
                ticket=ticket,
                order_item=item,
                quantity=item.quantity,
                special_request=item.special_request,
            )
            item.status = 'sent'
            item.save()

    order.status = 'sent'
    order.save()

    return JsonResponse({
        'ok': True,
        'ticket_number': ticket_number,
        'kitchen_items': len(kitchen_items),
        'bar_items_ready': len(bar_items),
    })


# =============================================================================
# Kitchen Display
# =============================================================================

def _kitchen_context(tenant):
    """ข้อมูลตั๋วครัว + เชฟเข้ากะวันนี้ — ใช้ร่วมกันระหว่างหน้าเต็มและ partial (HTMX)"""
    tickets = KitchenTicket.objects.filter(
        tenant=tenant,
        status__in=['pending', 'in_progress'],
        created_at__date=timezone.now().date(),
    ).select_related('order', 'table', 'prepared_by').prefetch_related('items__order_item__menu_item')

    from hr.models import ShiftSchedule
    kitchen_staff = [
        s.employee for s in
        ShiftSchedule.objects.filter(
            employee__tenant=tenant,
            date=timezone.now().date(),
            employee__position__in=('chef', 'sous_chef', 'cook'),
        ).select_related('employee')
    ]
    return {
        'tickets': tickets,
        'total_tickets': tickets.count(),
        'kitchen_staff': kitchen_staff,
    }


@require_kitchen
def kitchen_display(request):
    tenant = request.user.tenant
    if not tenant:
        return render(request, 'pos/kitchen_display.html', {'no_tenant': True})
    return render(request, 'pos/kitchen_display.html', _kitchen_context(tenant))


@require_kitchen
def kitchen_grid(request):
    """Partial — กริดตั๋วครัวสำหรับ HTMX poll (อัปเดตสดทุก 5 วิ)"""
    tenant = request.user.tenant
    if not tenant:
        return render(request, 'pos/_kitchen_tickets.html', {'tickets': [], 'total_tickets': 0})
    return render(request, 'pos/_kitchen_tickets.html', _kitchen_context(tenant))


@require_POST
def update_ticket(request, ticket_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    ticket = get_object_or_404(KitchenTicket, id=ticket_id, tenant=tenant)

    data = json.loads(request.body)
    action = data.get('action')

    if action == 'start':
        ticket.status = 'in_progress'
        ticket.save()
    elif action == 'done':
        ticket.status = 'done'
        ticket.completed_at = timezone.now()
        ticket.save()
        # Update order items to ready
        for ti in ticket.items.all():
            ti.order_item.status = 'ready'
            ti.order_item.save()
            ti.is_done = True
            ti.save()
    elif action == 'item_done':
        item_id = data.get('item_id')
        ti = get_object_or_404(KitchenTicketItem, id=item_id, ticket=ticket)
        ti.is_done = True
        ti.save()
        ti.order_item.status = 'ready'
        ti.order_item.save()
        # Check if all items done
        if not ticket.items.filter(is_done=False).exists():
            ticket.status = 'done'
            ticket.completed_at = timezone.now()
            ticket.save()
    elif action == 'assign_chef':
        from hr.models import Employee
        chef_id = data.get('chef_id')
        if chef_id:
            chef = get_object_or_404(Employee, id=chef_id)
            ticket.prepared_by = chef
            ticket.save(update_fields=['prepared_by'])

    return JsonResponse({'ok': True, 'status': ticket.status})


# =============================================================================
# Upsell Engine
# =============================================================================

def get_upsell_suggestions(tenant, order):
    """วิเคราะห์ guest profile แล้วแนะนำเมนู"""
    men = order.men_count
    women = order.women_count
    children = order.children_count
    senior = order.senior_count
    total = order.guest_count

    # Determine profile type
    profiles = []

    if men == 1 and women == 1 and children == 0 and total == 2:
        profiles.append('couple')
    if children > 0:
        profiles.append('has_children')
    if senior > 0:
        profiles.append('has_senior')
    if total >= 4:
        profiles.append('group')
    if men > 0 and women == 0 and children == 0 and senior == 0:
        profiles.append('men_only')
    if women > 0 and men == 0 and children == 0 and senior == 0:
        profiles.append('women_only')

    if not profiles:
        profiles.append('default')

    # Get already ordered menu_item ids
    ordered_ids = list(
        order.items.filter(is_voided=False).values_list('menu_item_id', flat=True)
    )

    rules = MenuUpsellRule.objects.filter(
        tenant=tenant,
        profile_type__in=profiles,
        is_active=True,
        menu_item__is_available=True,
    ).exclude(
        menu_item_id__in=ordered_ids,
    ).select_related('menu_item', 'menu_item__recipe').order_by('-priority')[:3]

    suggestions = []
    for rule in rules:
        mi = rule.menu_item
        suggestions.append({
            'menu_item': mi,
            'reason': rule.reason,
            'gp_pct': mi.food_cost_pct,
            'price': mi.selling_price,
        })

    return suggestions


# =============================================================================
# Payment
# =============================================================================

def payment_view(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)
    order_items = order.items.filter(is_voided=False).select_related('menu_item')

    context = {
        'order': order,
        'order_items': order_items,
        'payment_methods': Transaction.PaymentMethod.choices,
    }
    return render(request, 'pos/payment.html', context)


@require_POST
def process_payment(request, order_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)

    data = json.loads(request.body)
    method = data.get('payment_method', 'cash')
    received = Decimal(str(data.get('received', order.total)))
    reference = data.get('reference', '')

    change = max(received - order.total, Decimal('0'))

    Transaction.objects.create(
        tenant=tenant,
        order=order,
        payment_method=method,
        amount=order.total,
        received=received,
        change=change,
        reference=reference,
        processed_by=request.user,
    )

    order.status = 'paid'
    order.closed_at = timezone.now()
    order.save()

    # Free up table
    if order.table:
        order.table.status = 'empty'
        order.table.save()

    return JsonResponse({
        'ok': True,
        'change': str(change),
        'order_number': order.order_number,
    })


# =============================================================================
# API — Order data for polling
# =============================================================================

def order_data(request, order_id):
    """JSON endpoint for polling order state"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    order = get_object_or_404(Order, id=order_id, tenant=tenant)
    items = order.items.filter(is_voided=False).select_related('menu_item')

    return JsonResponse({
        'order_number': order.order_number,
        'status': order.status,
        'subtotal': str(order.subtotal),
        'total': str(order.total),
        'guest_count': order.guest_count,
        'duration': order.duration_minutes,
        'items': [{
            'id': i.id,
            'name': i.menu_item.name,
            'qty': i.quantity,
            'price': str(i.unit_price),
            'total': str(i.line_total),
            'status': i.status,
            'special': i.special_request,
        } for i in items],
    })


def kitchen_data(request):
    """JSON endpoint for kitchen display polling"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tenant = request.user.tenant
    tickets = KitchenTicket.objects.filter(
        tenant=tenant,
        status__in=['pending', 'in_progress'],
        created_at__date=timezone.now().date(),
    ).select_related('order', 'table').prefetch_related('items__order_item__menu_item')

    return JsonResponse({
        'tickets': [{
            'id': t.id,
            'ticket_number': t.ticket_number,
            'table': t.table.number if t.table else 'N/A',
            'status': t.status,
            'minutes_ago': int((timezone.now() - t.created_at).total_seconds() / 60),
            'items': [{
                'id': ti.id,
                'name': ti.order_item.menu_item.name,
                'qty': ti.quantity,
                'special': ti.special_request,
                'is_done': ti.is_done,
                'prep_time': ti.order_item.menu_item.prep_time_minutes,
            } for ti in t.items.all()],
        } for t in tickets],
    })
