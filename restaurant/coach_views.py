"""
AI โค้ชพนักงาน — วิเคราะห์ผลงานขายแต่ละคน + ให้คำแนะนำพัฒนา (ด้วย Claude)
ช่วยผู้จัดการพัฒนาทีม: เห็นใครเก่งอะไร ควรเชียร์/ฝึกอะไรเพิ่ม
"""
import json
import logging

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import require_manager
from accounts.models import User
from pos.services import staff_performance

logger = logging.getLogger(__name__)


def _client():
    try:
        from django.conf import settings
        key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        if not key:
            return None
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        return None


def _require_back_office(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.can_access_back_office:
        return render(request, 'includes/no_access.html', {'message': 'เฉพาะผู้จัดการ/GM'}, status=403)
    return None


def coach_team(request):
    """หน้าโค้ชทีม — ผลงานพนักงาน + ปุ่มขอคำแนะนำ AI"""
    block = _require_back_office(request)
    if block:
        return block
    perf = staff_performance(request.user.tenant, days=30)
    return render(request, 'restaurant/coach_team.html', {
        'perf': perf,
        'has_api': _client() is not None,
    })


@require_POST
def coach_suggest(request):
    """ขอคำแนะนำพัฒนาพนักงาน 1 คน (AI)"""
    if not request.user.is_authenticated or not request.user.can_access_back_office:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    tenant = request.user.tenant
    user_id = json.loads(request.body).get('user_id')
    perf = {p['user'].id: p for p in staff_performance(tenant, days=30)}
    p = perf.get(user_id)
    if not p:
        return JsonResponse({'ok': False, 'error': 'ไม่พบข้อมูลพนักงาน'}, status=404)

    cats = ', '.join(f'{k} {v} จาน' for k, v in list(p['categories'].items())[:5]) or 'ยังไม่มีข้อมูล'
    client = _client()
    if not client:
        # โหมด demo — แนะนำจากกฎพื้นฐาน
        tips = _rule_based_tips(p)
        return JsonResponse({'ok': True, 'tips': tips, 'demo': True})

    prompt = f"""คุณเป็นโค้ช/ผู้จัดการร้านอาหารที่ใส่ใจพัฒนาทีมงาน
ข้อมูลพนักงาน "{p['name']}" รอบ 30 วัน:
- ออเดอร์ที่ดูแล: {p['orders']}
- ยอดขายรวม: {p['revenue']:.0f} บาท
- เฉลี่ยต่อหัวลูกค้า: {p['avg_check']:.0f} บาท
- เมนูที่ขายเด่น: {cats}

ช่วยให้คำแนะนำพัฒนา 3 ข้อ แบบเป็นกันเอง ให้กำลังใจ และทำได้จริง
เพื่อเพิ่มยอดขาย + พัฒนาทักษะพนักงานคนนี้
ตอบเป็น JSON array เท่านั้น: [{{"title":"หัวข้อสั้น","detail":"รายละเอียด 1-2 ประโยค"}}]"""

    try:
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001', max_tokens=700,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith('```'):
            text = text.strip('`').lstrip('json').strip()
        tips = json.loads(text)
        return JsonResponse({'ok': True, 'tips': tips})
    except Exception as exc:  # noqa: BLE001
        logger.error('coach suggest error: %s', exc)
        return JsonResponse({'ok': True, 'tips': _rule_based_tips(p), 'demo': True})


def _rule_based_tips(p):
    """คำแนะนำพื้นฐานเมื่อยังไม่มี AI (ใช้กฎจากข้อมูลจริง)"""
    tips = []
    if p['avg_check'] < 200:
        tips.append({'title': 'เพิ่มยอดต่อหัว',
                     'detail': f"เฉลี่ยต่อคน {p['avg_check']:.0f} บาท ลองเชียร์ของหวาน/เครื่องดื่มเพิ่มหลังลูกค้าสั่งอาหารหลัก"})
    else:
        tips.append({'title': 'รักษามาตรฐานยอดต่อหัว',
                     'detail': f"ยอดต่อคน {p['avg_check']:.0f} บาท ดีมาก ลองเป็นพี่เลี้ยงสอนทีมเรื่องการแนะนำเมนู"})
    tips.append({'title': 'ต่อยอดจุดแข็ง',
                 'detail': f"ขายเด่นหมวด {p['top_category']} — ใช้ความถนัดนี้เชียร์เมนูกำไรดีในหมวดเดียวกัน"})
    tips.append({'title': 'ตั้งเป้าเล็ก ๆ',
                 'detail': 'ตั้งเป้ารายวันร่วมกับแคมเปญเชียร์ขาย แล้วให้ฟีดแบ็กเชิงบวกเมื่อทำได้'})
    return tips
