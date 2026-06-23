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
