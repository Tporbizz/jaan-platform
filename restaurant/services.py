"""
Restaurant Automation Services
==============================
ตรรกะงานอัตโนมัติฝั่งวัตถุดิบ/จัดซื้อ — เรียกได้ทั้งจาก management command
(Render Cron) และ Celery task โดยไม่ผูกตาย Redis

  * auto_generate_reorder_pos — ของต่ำกว่าขั้นต่ำ → ใบสั่งซื้อ "ร่าง" รออนุมัติ (semi-auto)
  * scan_expiring_lots        — สแกน Lot ใกล้หมดอายุ → แจ้งเตือน
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

ZERO = Decimal('0')

# สถานะ PO ที่ถือว่า "ยังค้างอยู่" — ไม่ควรสั่งซ้ำ
_OPEN_PO_STATUSES = ('draft', 'sent', 'partial')


def _items_below_min(tenant):
    from .models import Item

    return (
        Item.objects
        .filter(tenant=tenant, is_active=True, current_stock__lt=F('min_stock'))
        .select_related('default_supplier')
    )


def _resolve_supplier(tenant, item):
    """หา supplier: default ก่อน, ถ้าไม่มีใช้ supplier จาก PO ล่าสุด"""
    if item.default_supplier:
        return item.default_supplier
    from .models import POItem

    last = (
        POItem.objects
        .filter(item=item, purchase_order__tenant=tenant)
        .order_by('-purchase_order__order_date')
        .select_related('purchase_order__supplier')
        .first()
    )
    return last.purchase_order.supplier if last else None


@transaction.atomic
def auto_generate_reorder_pos(tenant, user=None):
    """
    สร้างใบสั่งซื้อร่างอัตโนมัติสำหรับของที่ต่ำกว่าขั้นต่ำ จัดกลุ่มตาม supplier
    ข้ามวัตถุดิบที่มีอยู่ใน PO ที่ยังค้างอยู่แล้ว (กันสั่งซ้ำ)

    คืนค่า: list ของ PurchaseOrder ที่สร้างใหม่
    """
    from .models import PurchaseOrder, POItem

    low_items = _items_below_min(tenant)

    # วัตถุดิบที่อยู่ใน PO ค้างอยู่แล้ว → ข้าม
    already_ordered = set(
        POItem.objects
        .filter(purchase_order__tenant=tenant, purchase_order__status__in=_OPEN_PO_STATUSES)
        .values_list('item_id', flat=True)
    )

    # จัดกลุ่มตาม supplier
    groups = {}
    for item in low_items:
        if item.id in already_ordered:
            continue
        supplier = _resolve_supplier(tenant, item)
        if not supplier:
            continue  # ไม่มี supplier — ข้าม (ให้คนจัดการเอง)
        need = (item.max_stock - item.current_stock) if item.max_stock else (item.min_stock * 2)
        need = max(need, ZERO)
        if need <= 0:
            continue
        groups.setdefault(supplier, []).append((item, need))

    if not groups:
        return []

    today = timezone.now()
    prefix = today.strftime('%y%m%d')
    seq = PurchaseOrder.objects.filter(tenant=tenant, po_number__startswith=prefix).count()

    created = []
    for supplier, lines in groups.items():
        seq += 1
        po = PurchaseOrder.objects.create(
            tenant=tenant,
            po_number=f"{prefix}-A{seq:02d}",  # A = auto
            supplier=supplier,
            status=PurchaseOrder.Status.DRAFT,
            order_date=today.date(),
            created_by=user,
            notes='สร้างอัตโนมัติจากระบบเติมสต็อก',
        )
        for item, need in lines:
            POItem.objects.create(
                purchase_order=po, item=item,
                quantity=need, unit_price=item.cost_per_unit,
            )
        created.append(po)

    return created


def scan_expiring_lots(tenant, days=3):
    """คืน list ของ LotBatch ที่จะหมดอายุภายใน N วัน และยังมีของเหลือ"""
    from .models import LotBatch

    today = timezone.localdate()
    return list(
        LotBatch.objects
        .filter(
            tenant=tenant, quantity__gt=0,
            expiry_date__isnull=False,
            expiry_date__lte=today + timezone.timedelta(days=days),
        )
        .select_related('item')
        .order_by('expiry_date')
    )


def scan_low_stock(tenant):
    """คืน list ของวัตถุดิบที่ต่ำกว่าขั้นต่ำ"""
    return list(_items_below_min(tenant))


def receive_stock(tenant, item, qty, unit_cost, supplier=None, expiry_date=None,
                  user=None, reference='BILL'):
    """
    รับวัตถุดิบเข้าสต็อกแบบไม่ผูก PO (เช่น จากการสแกนบิล/ซื้อสด)
    สร้าง LotBatch + StockMovement (in) + อัปเดตสต็อกและต้นทุนล่าสุด
    """
    from .models import LotBatch, StockMovement, PriceHistory

    qty = Decimal(str(qty))
    unit_cost = Decimal(str(unit_cost))
    if qty <= 0:
        return None
    today = timezone.localdate()

    LotBatch.objects.create(
        tenant=tenant, item=item,
        lot_number=f"{reference}-{(item.code or item.name[:6])}",
        received_date=today, expiry_date=expiry_date or None,
        quantity=qty, cost_per_unit=unit_cost, supplier=supplier,
    )

    # บันทึกประวัติราคาถ้าราคาเปลี่ยน
    old = item.cost_per_unit or ZERO
    if old > 0 and unit_cost != old:
        PriceHistory.objects.create(
            tenant=tenant, item=item, old_price=old, new_price=unit_cost,
            change_pct=((unit_cost - old) / old) * 100,
            recorded_by=user, notes='อัปเดตจากการสแกนบิล',
        )

    item.current_stock = (item.current_stock or ZERO) + qty
    item.cost_per_unit = unit_cost  # อัปเดตเป็นราคาล่าสุดจากบิล
    if supplier and not item.default_supplier:
        item.default_supplier = supplier
    item.save(update_fields=['current_stock', 'cost_per_unit', 'default_supplier'])

    StockMovement.objects.create(
        tenant=tenant, item=item, movement_type='in', quantity=qty,
        unit_cost=unit_cost, reference=reference, created_by=user,
        notes='รับเข้าจากการสแกนบิล',
    )
    return item
