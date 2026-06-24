import json
from decimal import Decimal

from django.db.models import Sum, F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from restaurant.models import MenuItem
from .models import EventOrder, EventOrderItem, EventSession


def event_list(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    sessions = EventSession.objects.filter(tenant=tenant)
    return render(request, 'events/event_list.html', {'sessions': sessions})


def event_create(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    menu_items = MenuItem.objects.filter(tenant=tenant, is_available=True)

    if request.method == 'POST':
        name = request.POST.get('name', '')
        location = request.POST.get('location', '')
        date = request.POST.get('date', str(timezone.localdate()))

        snapshot = []
        for mi in menu_items:
            price_str = request.POST.get(f'price_{mi.id}', '')
            if price_str:
                snapshot.append({
                    'id': mi.id, 'name': mi.name, 'name_en': mi.name_en,
                    'price': str(Decimal(price_str)),
                    'category': mi.get_menu_category_display(),
                })

        session = EventSession.objects.create(
            tenant=tenant, name=name, location=location, date=date,
            menu_snapshot=snapshot, created_by=request.user,
        )
        return redirect('events:event_dashboard', session_id=session.id)

    return render(request, 'events/event_create.html', {'menu_items': menu_items})


def event_dashboard(request, session_id):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    session = get_object_or_404(EventSession, id=session_id, tenant=tenant)
    orders = session.orders.all()
    paid_orders = orders.filter(status='paid')

    top_items = EventOrderItem.objects.filter(
        order__session=session, order__status='paid',
    ).values('menu_item_name').annotate(
        total_qty=Sum('quantity'),
        total_rev=Sum(F('quantity') * F('unit_price')),
    ).order_by('-total_qty')[:5]

    paid_total = sum(o.total for o in paid_orders)
    context = {
        'session': session,
        'orders': orders[:30],
        'total_revenue': paid_total,
        'total_orders': paid_orders.count(),
        'avg_order': (paid_total / paid_orders.count()) if paid_orders.count() else 0,
        'top_items': top_items,
    }
    return render(request, 'events/event_dashboard.html', context)


@require_POST
def event_toggle(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    tenant = request.user.tenant
    session = get_object_or_404(EventSession, id=session_id, tenant=tenant)
    if session.status == 'draft':
        session.status = 'active'
    elif session.status == 'active':
        session.status = 'closed'
        session.recalculate_totals()
    session.save()
    return JsonResponse({'ok': True, 'status': session.status})


# --- Public QR Menu (no login) ---

def public_menu(request, session_token):
    session = get_object_or_404(EventSession, session_token=session_token, status='active')
    return render(request, 'events/public_menu.html', {'session': session})


@csrf_exempt
@require_POST
def public_order(request, session_token):
    session = get_object_or_404(EventSession, session_token=session_token, status='active')
    data = json.loads(request.body)
    items = data.get('items', [])
    if not items:
        return JsonResponse({'error': 'No items'}, status=400)

    count = session.orders.count() + 1
    order = EventOrder.objects.create(
        session=session, order_number=f"EV{session.id:03d}-{count:04d}",
        customer_name=data.get('customer_name', ''),
    )

    menu_map = {m['id']: m for m in session.menu_snapshot}
    for entry in items:
        mi = menu_map.get(entry.get('menu_item_id'))
        qty = int(entry.get('quantity', 1))
        if mi and qty > 0:
            EventOrderItem.objects.create(
                order=order, menu_item_name=mi['name'],
                menu_item_id=mi['id'], quantity=qty,
                unit_price=Decimal(mi['price']),
            )
    order.recalculate()
    return JsonResponse({'ok': True, 'order_number': order.order_number, 'total': str(order.total)})


@csrf_exempt
@require_POST
def public_pay(request, session_token, order_id):
    session = get_object_or_404(EventSession, session_token=session_token, status='active')
    order = get_object_or_404(EventOrder, id=order_id, session=session)
    order.status = 'paid'
    order.payment_method = 'promptpay'
    order.save()
    session.recalculate_totals()
    return JsonResponse({'ok': True, 'order_number': order.order_number})
