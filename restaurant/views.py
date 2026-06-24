import json
from decimal import Decimal

from django.db.models import Sum, Count, Q, F, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import require_stock
from .models import (
    Category, Item, LotBatch, POItem, PriceHistory, PurchaseOrder,
    StockMovement, Supplier, WasteRecord, KPITarget, MenuItem,
)


@require_stock
def stock_dashboard(request):
    tenant = request.user.tenant
    today = timezone.localdate()

    if not tenant:
        return render(request, 'restaurant/stock_dashboard.html', {'no_tenant': True})

    # Items
    items = Item.objects.filter(tenant=tenant, is_active=True)
    total_items = items.count()
    below_min = items.filter(current_stock__lt=F('min_stock')).order_by('current_stock')
    out_of_stock = items.filter(current_stock__lte=0)

    # Stock value — aggregate ครั้งเดียว (กัน N+1 กับวัตถุดิบหลายร้อยรายการ)
    from django.db.models import DecimalField, ExpressionWrapper, Q
    total_stock_value = items.aggregate(
        v=Sum(ExpressionWrapper(F('current_stock') * F('cost_per_unit'),
                                output_field=DecimalField(max_digits=14, decimal_places=2)))
    )['v'] or Decimal('0')

    # ค้นหา + กรองหมวด สำหรับตารางวัตถุดิบ (รองรับ 600+ รายการ)
    q = request.GET.get('q', '').strip()
    cat_id = request.GET.get('cat', '').strip()
    status = request.GET.get('status', '').strip()
    item_qs = items.select_related('category', 'unit')
    if q:
        item_qs = item_qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if cat_id:
        item_qs = item_qs.filter(category_id=cat_id)
    if status == 'low':
        item_qs = item_qs.filter(current_stock__lt=F('min_stock'))
    elif status == 'out':
        item_qs = item_qs.filter(current_stock__lte=0)
    item_qs = item_qs.order_by('category__name', 'name')
    item_match_count = item_qs.count()
    item_categories = Category.objects.filter(tenant=tenant).order_by('name')

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
        'items': item_qs[:200],
        'item_match_count': item_match_count,
        'item_categories': item_categories,
        'q': q,
        'cat_id': cat_id,
        'status': status,
    }
    return render(request, 'restaurant/stock_dashboard.html', context)


# =============================================================================
# Phase 2.1 — Smart Reorder
# =============================================================================

@require_stock
def reorder_list(request):
    tenant = request.user.tenant
    if not tenant:
        return render(request, 'restaurant/reorder_list.html', {'no_tenant': True})

    # Items ที่ stock ต่ำกว่า min_stock
    low_items = Item.objects.filter(
        tenant=tenant, is_active=True,
        current_stock__lt=F('min_stock'),
    ).select_related('category', 'unit', 'default_supplier')

    # เติม suggested supplier จาก last PO ถ้าไม่มี default_supplier
    items_data = []
    for item in low_items:
        supplier = item.default_supplier
        if not supplier:
            last_po_item = POItem.objects.filter(
                item=item, purchase_order__tenant=tenant,
            ).order_by('-purchase_order__order_date').first()
            if last_po_item:
                supplier = last_po_item.purchase_order.supplier

        suggested_qty = item.max_stock - item.current_stock if item.max_stock else item.min_stock * 2
        items_data.append({
            'item': item,
            'supplier': supplier,
            'suggested_qty': max(suggested_qty, 0),
            'estimated_cost': max(suggested_qty, 0) * item.cost_per_unit,
        })

    suppliers = Supplier.objects.filter(tenant=tenant, is_active=True)

    context = {
        'items_data': items_data,
        'total_items': len(items_data),
        'total_estimated': sum(d['estimated_cost'] for d in items_data),
        'suppliers': suppliers,
    }
    return render(request, 'restaurant/reorder_list.html', context)


@require_stock
@require_POST
def create_pos_from_reorder(request):
    tenant = request.user.tenant
    if not tenant:
        return JsonResponse({'error': 'No tenant'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    items_list = data.get('items', [])
    if not items_list:
        return JsonResponse({'error': 'No items selected'}, status=400)

    # Group by supplier
    supplier_groups = {}
    for entry in items_list:
        item_id = entry.get('item_id')
        supplier_id = entry.get('supplier_id')
        quantity = Decimal(str(entry.get('quantity', 0)))

        if not item_id or not supplier_id or quantity <= 0:
            continue

        if supplier_id not in supplier_groups:
            supplier_groups[supplier_id] = []
        supplier_groups[supplier_id].append({
            'item_id': item_id,
            'quantity': quantity,
        })

    if not supplier_groups:
        return JsonResponse({'error': 'No valid items'}, status=400)

    # Generate PO number prefix
    today = timezone.now()
    po_prefix = today.strftime('%y%m%d')
    existing_count = PurchaseOrder.objects.filter(
        tenant=tenant, po_number__startswith=po_prefix,
    ).count()

    created_pos = []
    for supplier_id, line_items in supplier_groups.items():
        supplier = Supplier.objects.get(id=supplier_id, tenant=tenant)
        existing_count += 1
        po_number = f"{po_prefix}-{existing_count:02d}"

        po = PurchaseOrder.objects.create(
            tenant=tenant,
            po_number=po_number,
            supplier=supplier,
            status='draft',
            order_date=today.date(),
            created_by=request.user,
        )

        for li in line_items:
            item = Item.objects.get(id=li['item_id'], tenant=tenant)
            POItem.objects.create(
                purchase_order=po,
                item=item,
                quantity=li['quantity'],
                unit_price=item.cost_per_unit,
            )

        created_pos.append({
            'id': po.id,
            'po_number': po.po_number,
            'supplier': supplier.name,
            'item_count': len(line_items),
            'total': str(po.total_amount),
        })

    return JsonResponse({'created': created_pos, 'count': len(created_pos)})


# =============================================================================
# Phase 2.2 — Goods Receipt
# =============================================================================

@require_stock
def goods_receipt(request, po_id):
    tenant = request.user.tenant
    po = get_object_or_404(PurchaseOrder, id=po_id, tenant=tenant)
    po_items = po.items.select_related('item', 'item__unit')

    price_alerts = []
    success = False

    if request.method == 'POST':
        today = timezone.localdate()
        all_received = True

        for po_item in po_items:
            qty_key = f"qty_{po_item.id}"
            price_key = f"price_{po_item.id}"
            expiry_key = f"expiry_{po_item.id}"

            actual_qty = Decimal(request.POST.get(qty_key, '0') or '0')
            actual_price = Decimal(request.POST.get(price_key, '0') or '0')
            expiry_date = request.POST.get(expiry_key, '').strip() or None

            if actual_qty <= 0:
                if po_item.received_quantity < po_item.quantity:
                    all_received = False
                continue

            # Update received quantity
            po_item.received_quantity += actual_qty
            po_item.save()

            if po_item.received_quantity < po_item.quantity:
                all_received = False

            # Create LotBatch
            lot_number = f"PO{po.po_number}-{po_item.item.name[:6]}"
            LotBatch.objects.create(
                tenant=tenant,
                item=po_item.item,
                lot_number=lot_number,
                received_date=today,
                expiry_date=expiry_date or None,
                quantity=actual_qty,
                cost_per_unit=actual_price,
                supplier=po.supplier,
            )

            # Update item stock
            po_item.item.current_stock += actual_qty
            po_item.item.save()

            # Create StockMovement
            StockMovement.objects.create(
                tenant=tenant,
                item=po_item.item,
                movement_type='in',
                quantity=actual_qty,
                unit_cost=actual_price,
                reference=f"PO-{po.po_number}",
                created_by=request.user,
            )

            # Price change detection
            old_price = po_item.unit_price
            if actual_price != old_price and old_price > 0:
                change_pct = ((actual_price - old_price) / old_price) * 100

                PriceHistory.objects.create(
                    tenant=tenant,
                    item=po_item.item,
                    old_price=old_price,
                    new_price=actual_price,
                    purchase_order=po,
                    recorded_by=request.user,
                )

                # Update item cost
                po_item.item.cost_per_unit = actual_price
                po_item.item.save()

                if abs(change_pct) > 5:
                    price_alerts.append({
                        'item': po_item.item.name,
                        'old': old_price,
                        'new': actual_price,
                        'pct': round(change_pct, 1),
                        'war': abs(change_pct) > 10,
                    })

        # Update PO status
        if all_received:
            po.status = 'received'
            po.received_date = today
        else:
            po.status = 'partial'
        po.save()

        success = True

    context = {
        'po': po,
        'po_items': po_items,
        'price_alerts': price_alerts,
        'success': success,
    }
    return render(request, 'restaurant/goods_receipt.html', context)


def po_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'restaurant/po_list.html', {'no_tenant': True})

    status_filter = request.GET.get('status', '')
    pos = PurchaseOrder.objects.filter(tenant=tenant).select_related('supplier', 'created_by')

    if status_filter:
        pos = pos.filter(status=status_filter)

    context = {
        'pos': pos,
        'status_filter': status_filter,
        'status_choices': PurchaseOrder.Status.choices,
    }
    return render(request, 'restaurant/po_list.html', context)


# =============================================================================
# Phase 2.2 — Bulk Price Update
# =============================================================================

def bulk_price_update(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'restaurant/bulk_price_update.html', {'no_tenant': True})

    items = Item.objects.filter(tenant=tenant, is_active=True).select_related('category', 'unit')
    updated = []
    war_mode = False

    if request.method == 'POST':
        for item in items:
            new_price_str = request.POST.get(f"price_{item.id}", '').strip()
            reason = request.POST.get(f"reason_{item.id}", 'market')

            if not new_price_str:
                continue

            new_price = Decimal(new_price_str)
            if new_price == item.cost_per_unit:
                continue

            old_price = item.cost_per_unit
            change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0

            PriceHistory.objects.create(
                tenant=tenant,
                item=item,
                old_price=old_price,
                new_price=new_price,
                reason=reason,
                recorded_by=request.user,
            )

            item.cost_per_unit = new_price
            item.save()

            entry = {
                'name': item.name,
                'old': old_price,
                'new': new_price,
                'pct': round(change_pct, 1),
            }
            updated.append(entry)

            if change_pct > 10:
                war_mode = True

    # Recent price changes
    recent_changes = PriceHistory.objects.filter(tenant=tenant)[:20]

    context = {
        'items': items,
        'updated': updated,
        'war_mode': war_mode,
        'recent_changes': recent_changes,
        'reasons': PriceHistory.ChangeReason.choices,
    }
    return render(request, 'restaurant/bulk_price_update.html', context)


# =============================================================================
# Market List — รายการตลาด (print-friendly, mobile-friendly)
# =============================================================================

def market_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    if not tenant:
        return render(request, 'restaurant/market_list.html', {'no_tenant': True})

    # Items ต่ำกว่า min_stock + items ที่ user เพิ่มเอง (manual)
    low_items = Item.objects.filter(
        tenant=tenant, is_active=True,
        current_stock__lt=F('min_stock'),
    ).select_related('category', 'unit', 'default_supplier')

    # จัดกลุ่มตาม supplier
    supplier_groups = {}
    no_supplier_items = []

    for item in low_items:
        supplier = item.default_supplier
        if not supplier:
            # ลองหาจาก PO ล่าสุด
            last_po_item = POItem.objects.filter(
                item=item, purchase_order__tenant=tenant,
            ).order_by('-purchase_order__order_date').first()
            if last_po_item:
                supplier = last_po_item.purchase_order.supplier

        need_qty = item.max_stock - item.current_stock if item.max_stock else item.min_stock * 2
        need_qty = max(need_qty, 0)
        est_cost = need_qty * item.cost_per_unit

        entry = {
            'item': item,
            'need_qty': need_qty,
            'est_cost': est_cost,
        }

        if supplier:
            if supplier.id not in supplier_groups:
                supplier_groups[supplier.id] = {
                    'supplier': supplier,
                    'items': [],
                    'total': 0,
                }
            supplier_groups[supplier.id]['items'].append(entry)
            supplier_groups[supplier.id]['total'] += est_cost
        else:
            no_supplier_items.append(entry)

    # แปลงเป็น list เรียงตามชื่อ supplier
    groups = sorted(supplier_groups.values(), key=lambda g: g['supplier'].name)
    grand_total = sum(g['total'] for g in groups) + sum(e['est_cost'] for e in no_supplier_items)

    context = {
        'groups': groups,
        'no_supplier_items': no_supplier_items,
        'grand_total': grand_total,
        'total_items': low_items.count(),
        'today': timezone.localdate(),
    }
    return render(request, 'restaurant/market_list.html', context)
