"""
สแกนบิล supplier (Makro ฯลฯ) ด้วย Claude Vision → อ่านรายการสินค้า → คีย์เข้าสต็อก
ผู้ใช้ทบทวน/แก้ก่อนยืนยัน (human-in-the-loop) แล้วระบบรับเข้าสต็อกให้อัตโนมัติ
"""
import base64
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from accounts.decorators import require_stock
from .models import Item, Supplier
from .services import receive_stock

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """นี่คือรูปใบเสร็จ/บิลซื้อวัตถุดิบจาก supplier (เช่น Makro, ตลาดสด).
อ่านข้อมูลจากบิลแล้วดึงออกมาเป็น JSON ตามรูปแบบนี้เท่านั้น (ห้ามมี markdown หรือคำอธิบายอื่น):
{
  "supplier": "ชื่อร้าน/supplier ที่ออกบิล",
  "date": "วันที่ในบิล (YYYY-MM-DD ถ้าอ่านได้)",
  "items": [
    {"name": "ชื่อสินค้า", "qty": ตัวเลขจำนวน, "unit": "หน่วย", "unit_price": ราคาต่อหน่วย, "total": ราคารวมบรรทัด}
  ]
}
กฎ:
- qty, unit_price, total เป็นตัวเลขเท่านั้น (ไม่มีคอมมา/สัญลักษณ์เงิน)
- ถ้าอ่านบางช่องไม่ได้ ใส่ 0 หรือ ""
- เอาเฉพาะรายการสินค้า ไม่เอายอดรวม/ภาษี/ส่วนลด
ตอบ JSON อย่างเดียว"""


def _client():
    """Anthropic client ถ้าตั้งค่า key + ติดตั้ง package แล้ว"""
    try:
        from django.conf import settings
        key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        if not key:
            return None
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        return None


@require_stock
def scan_bill(request):
    """หน้าอัปโหลด/ถ่ายบิล"""
    tenant = request.user.tenant
    items = Item.objects.filter(tenant=tenant, is_active=True).select_related('unit')
    items_json = [
        {'id': it.id, 'code': it.code, 'name': it.name,
         'unit': it.unit.abbreviation if it.unit else '', 'cost': float(it.cost_per_unit)}
        for it in items
    ]
    return render(request, 'restaurant/scan_bill.html', {
        'has_api': _client() is not None,
        'items_json': items_json,
    })


@require_stock
@require_POST
def scan_bill_extract(request):
    """รับรูปบิล → ส่งให้ Claude อ่าน → คืนรายการสินค้า (JSON)"""
    upload = request.FILES.get('bill')
    if not upload:
        return JsonResponse({'ok': False, 'error': 'ไม่พบรูปบิล'}, status=400)

    client = _client()
    if not client:
        return JsonResponse({
            'ok': False,
            'error': 'ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY — สแกนบิลอัตโนมัติยังใช้ไม่ได้ '
                     '(คีย์เองได้ที่หน้ารับของ)',
        }, status=503)

    media_type = upload.content_type or 'image/jpeg'
    img_b64 = base64.standard_b64encode(upload.read()).decode()

    try:
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=3000,
            messages=[{'role': 'user', 'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': img_b64}},
                {'type': 'text', 'text': EXTRACT_PROMPT},
            ]}],
        )
        text = resp.content[0].text.strip()
        if text.startswith('```'):
            text = text.strip('`').lstrip('json').strip()
        data = json.loads(text)
        return JsonResponse({'ok': True, **data})
    except Exception as exc:  # noqa: BLE001
        logger.error('scan bill extract error: %s', exc)
        return JsonResponse({'ok': False, 'error': f'อ่านบิลไม่สำเร็จ: {exc}'}, status=500)


@require_stock
@require_POST
def scan_bill_receive(request):
    """ยืนยันรายการที่ทบทวนแล้ว → รับเข้าสต็อก (สร้าง Lot + StockMovement)"""
    tenant = request.user.tenant
    data = json.loads(request.body)
    supplier_name = (data.get('supplier') or '').strip()
    items = data.get('items', [])

    supplier = None
    if supplier_name:
        supplier, _ = Supplier.objects.get_or_create(tenant=tenant, name=supplier_name)

    received = 0
    for row in items:
        item_id = row.get('item_id')
        qty = row.get('qty') or 0
        price = row.get('unit_price') or 0
        expiry = (row.get('expiry') or '').strip() or None
        if not item_id or float(qty) <= 0:
            continue
        item = Item.objects.filter(id=item_id, tenant=tenant).first()
        if not item:
            continue
        receive_stock(tenant, item, qty, price, supplier=supplier,
                      expiry_date=expiry, user=request.user, reference='BILL')
        received += 1

    return JsonResponse({'ok': True, 'received': received})
