"""
POS Automation Services
=======================
เครื่องยนต์อัตโนมัติของฝั่งขาย — ตัดสต็อกวัตถุดิบตามสูตรเมื่อจ่ายเงิน (FIFO ตาม Lot)
และอัปเดตยอดขายรายวันให้อัตโนมัติ

ออกแบบให้:
  * Idempotent — เรียกซ้ำไม่ตัดสต็อกซ้ำ (กันด้วย Order.stock_depleted)
  * ไม่ต้องพึ่ง Redis/Celery — ทำงานแบบ synchronous ใน transaction
  * เก็บ "ต้นทุนจริง" (actual cost) ต่อรายการ เพื่อคำนวณ Food Cost จริงได้แม่นยำ
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

ZERO = Decimal('0')

# หมวดเมนูที่นับเป็น "เครื่องดื่ม" สำหรับแยกยอดขาย
BEVERAGE_CATEGORIES = {
    'cocktail', 'mocktail', 'smoothie', 'coffee', 'beer', 'soft_drink',
}


def _consume_lots(tenant, item, qty_needed):
    """
    ตัดวัตถุดิบจาก LotBatch แบบ FIFO (หมดอายุก่อน-รับก่อน) ตามจำนวนที่ต้องใช้
    คืนค่า: ต้นทุนจริงรวมที่ถูกใช้ไป (Decimal)

    ถ้า Lot ไม่พอ ส่วนที่เหลือคิดที่ cost_per_unit ปัจจุบันของวัตถุดิบ
    ถ้าไม่มี Lot เลย คิดทั้งหมดที่ cost_per_unit ปัจจุบัน
    """
    from restaurant.models import LotBatch

    remaining = Decimal(qty_needed)
    total_cost = ZERO

    lots = (
        LotBatch.objects
        .select_for_update()
        .filter(tenant=tenant, item=item, quantity__gt=0)
        .order_by('expiry_date', 'received_date', 'id')
    )
    for lot in lots:
        if remaining <= 0:
            break
        take = min(lot.quantity, remaining)
        total_cost += take * lot.cost_per_unit
        lot.quantity -= take
        lot.save(update_fields=['quantity'])
        remaining -= take

    # ส่วนที่ Lot ไม่ครอบคลุม → คิดที่ราคาปัจจุบัน
    if remaining > 0:
        total_cost += remaining * item.cost_per_unit

    return total_cost


@transaction.atomic
def deplete_stock_for_order(order, user=None):
    """
    ตัดสต็อกวัตถุดิบตามสูตรของทุกเมนูในออเดอร์ (ที่ไม่ถูกยกเลิก)

    - ปริมาณที่ใช้ต่อจาน = recipe_item.quantity / recipe.portions
    - ตัดจาก LotBatch แบบ FIFO และบันทึก StockMovement (out)
    - เก็บต้นทุนจริงไว้ที่ OrderItem.cost_snapshot
    - ตั้ง Order.stock_depleted = True เพื่อกันตัดซ้ำ

    คืนค่า True ถ้าตัดสำเร็จ, False ถ้าเคยตัดไปแล้ว
    """
    from restaurant.models import StockMovement
    from .models import Order

    # ล็อกแถวออเดอร์ + เช็คซ้ำใน DB (กัน race / double-submit)
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.stock_depleted:
        order.stock_depleted = True
        return False

    tenant = order.tenant
    items = (
        order.items
        .filter(is_voided=False)
        .select_related('menu_item', 'menu_item__recipe')
    )

    for oi in items:
        recipe = oi.menu_item.recipe
        if not recipe:
            continue
        portions = recipe.portions or 1
        line_cost = ZERO

        for ri in recipe.ingredients.select_related('item').all():
            consume = (ri.quantity / portions) * oi.quantity
            if consume <= 0:
                continue

            ing = ri.item
            actual_cost = _consume_lots(tenant, ing, consume)
            line_cost += actual_cost

            # ลดสต็อกรวมของวัตถุดิบ
            ing.current_stock = (ing.current_stock or ZERO) - consume
            ing.save(update_fields=['current_stock'])

            unit_cost = (actual_cost / consume) if consume else ZERO
            StockMovement.objects.create(
                tenant=tenant,
                item=ing,
                movement_type=StockMovement.MovementType.OUT,
                quantity=consume,
                unit_cost=unit_cost,
                reference=f"ORDER-{order.order_number}",
                created_by=user,
                notes=f"ตัดสต็อกอัตโนมัติจากการขาย: {oi.menu_item.name} x{oi.quantity}",
            )

        oi.cost_snapshot = line_cost
        oi.save(update_fields=['cost_snapshot'])

    locked.stock_depleted = True
    locked.save(update_fields=['stock_depleted'])
    order.stock_depleted = True
    return True


def recompute_daily_sales(tenant, date):
    """
    คำนวณ/อัปเดต DailySalesRecord ของวันนั้นใหม่ทั้งหมดจากออเดอร์ที่ชำระแล้ว
    (idempotent — เรียกกี่ครั้งก็ได้ผลเท่าเดิม)
    """
    from reports.models import DailySalesRecord
    from .models import Order, OrderItem

    paid = Order.objects.filter(tenant=tenant, status='paid', opened_at__date=date)

    total_revenue = paid.aggregate(s=Sum('total'))['s'] or ZERO
    total_covers = paid.aggregate(s=Sum('guest_count'))['s'] or 0

    # แยกรายได้เครื่องดื่ม vs อาหาร และต้นทุนจริง
    line_items = OrderItem.objects.filter(
        order__in=paid, is_voided=False,
    ).select_related('menu_item')

    beverage_revenue = ZERO
    food_cost_actual = ZERO
    for oi in line_items:
        if oi.menu_item.menu_category in BEVERAGE_CATEGORIES:
            beverage_revenue += oi.line_total
        food_cost_actual += oi.cost_snapshot or ZERO

    dine_in_revenue = total_revenue - beverage_revenue
    avg_check = (total_revenue / total_covers) if total_covers else ZERO

    record, _ = DailySalesRecord.objects.update_or_create(
        tenant=tenant, date=date,
        defaults={
            'dine_in_revenue': dine_in_revenue,
            'beverage_revenue': beverage_revenue,
            'total_revenue': total_revenue,
            'total_covers': total_covers,
            'avg_check': avg_check,
            'food_cost_actual': food_cost_actual,
        },
    )
    return record


# =============================================================================
# Sales Campaign — เป้าเชียร์ขาย + ค่าคอม + กระดานผู้นำ
# =============================================================================

def get_active_campaign(tenant, date=None):
    """แคมเปญที่เปิดใช้งานของวันนั้น (ดีฟอลต์ = วันนี้ตามเวลาไทย)"""
    from django.utils import timezone
    from .models import SalesCampaign

    date = date or timezone.localdate()
    return SalesCampaign.objects.filter(tenant=tenant, date=date, is_active=True).first()


def campaign_menu_ids(tenant, date=None):
    """set ของ menu_item_id ที่อยู่ในแคมเปญวันนี้ — ใช้ติดป้าย 'เชียร์วันนี้' บนหน้าออเดอร์"""
    campaign = get_active_campaign(tenant, date)
    if not campaign:
        return {}
    return {ci.menu_item_id: ci.commission_per_dish for ci in campaign.items.all()}


def campaign_progress(campaign):
    """
    คำนวณความคืบหน้าแคมเปญ + กระดานผู้นำ (ใครขายได้กี่จาน/ค่าคอมเท่าไหร่)
    อิงจากออเดอร์ที่ชำระแล้วของวัน campaign.date และคนขาย = order.created_by
    """
    from .models import OrderItem

    items = list(campaign.items.select_related('menu_item'))
    rate = {ci.menu_item_id: ci.commission_per_dish for ci in items}
    menu_ids = list(rate.keys())

    sold_by_menu = {mid: 0 for mid in menu_ids}
    staff = {}  # user_id -> {'name', 'dishes', 'commission'}

    if menu_ids:
        oi_qs = OrderItem.objects.filter(
            order__tenant=campaign.tenant, order__status='paid',
            order__opened_at__date=campaign.date,
            is_voided=False, menu_item_id__in=menu_ids,
        ).select_related('order', 'order__created_by')
        for oi in oi_qs:
            mid = oi.menu_item_id
            qty = oi.quantity
            sold_by_menu[mid] = sold_by_menu.get(mid, 0) + qty
            user = oi.order.created_by
            key = user.id if user else 0
            if key not in staff:
                name = (user.get_full_name() or user.username) if user else 'ไม่ระบุพนักงาน'
                staff[key] = {'name': name, 'dishes': 0, 'commission': ZERO}
            staff[key]['dishes'] += qty
            staff[key]['commission'] += qty * rate.get(mid, ZERO)

    item_rows = []
    for ci in items:
        sold = sold_by_menu.get(ci.menu_item_id, 0)
        item_rows.append({
            'menu': ci.menu_item,
            'target': ci.target_qty,
            'sold': sold,
            'remaining': max(ci.target_qty - sold, 0),
            'commission_per_dish': ci.commission_per_dish,
            'total_commission': sold * ci.commission_per_dish,
            'pct': min(round(sold / ci.target_qty * 100), 100) if ci.target_qty else 0,
        })

    leaderboard = sorted(staff.values(), key=lambda s: (-s['dishes'], -s['commission']))
    total_sold = sum(r['sold'] for r in item_rows)
    total_target = sum(r['target'] for r in item_rows)

    return {
        'campaign': campaign,
        'items': item_rows,
        'leaderboard': leaderboard,
        'total_sold': total_sold,
        'total_target': total_target,
        'total_pct': min(round(total_sold / total_target * 100), 100) if total_target else 0,
        'total_commission': sum(s['commission'] for s in staff.values()),
    }
