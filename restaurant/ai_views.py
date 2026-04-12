"""
AI Content Studio — ช่วย FB ตั้งชื่อเมนูตามแบรนด์ร้าน + gen content สำหรับ social media
ใช้ Claude API (Anthropic) สำหรับ generate content
"""
import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import MenuItem

logger = logging.getLogger(__name__)

# Restaurant brand context for AI prompts
BRAND_CONTEXT = """
ร้านสารข้าว (Sarakao) — ร้านอาหารใต้แท้จากตรัง ตั้งอยู่ใน Parima Hotel
แบรนด์: อาหารใต้แท้ ตรัง วัตถุดิบท้องถิ่นสดทุกวัน
USP:
- อาหารทะเลสดจากทะเลตรัง
- สูตรต้นตำรับ ปรุงสดใหม่ทุกจาน
- ผักพื้นบ้าน (เหลียง, ผักกูด, สะตอ)
- บรรยากาศอบอุ่น เหมือนกินที่บ้าน
กลุ่มเป้าหมาย: ครอบครัว, คู่รัก, นักท่องเที่ยว, คนรักอาหารใต้
โทนเสียง: อบอุ่น ใกล้ชิด เป็นกันเอง แต่มีความเป็นมืออาชีพ ภูมิใจในวัตถุดิบท้องถิ่น
"""


def _get_anthropic_client():
    """Get Anthropic client if API key is configured"""
    try:
        from django.conf import settings as django_settings
        api_key = getattr(django_settings, 'ANTHROPIC_API_KEY', None)
        if not api_key:
            return None
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


def ai_studio(request):
    """AI Content Studio main page"""
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = request.user.tenant
    menus = MenuItem.objects.filter(tenant=tenant, is_available=True).order_by('menu_category', 'name')

    # Group by category
    menu_by_cat = {}
    for m in menus:
        cat = m.get_menu_category_display()
        if cat not in menu_by_cat:
            menu_by_cat[cat] = []
        menu_by_cat[cat].append(m)

    has_api = _get_anthropic_client() is not None

    context = {
        'menu_by_cat': menu_by_cat,
        'menus': menus,
        'has_api': has_api,
        'categories': MenuItem.MenuCategory.choices,
    }
    return render(request, 'ai/studio.html', context)


@require_POST
def ai_generate_name(request):
    """Generate branded menu name suggestions"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    data = json.loads(request.body)
    menu_id = data.get('menu_id')
    current_name = data.get('current_name', '')
    description = data.get('description', '')

    tenant = request.user.tenant

    if menu_id:
        menu = get_object_or_404(MenuItem, id=menu_id, tenant=tenant)
        current_name = menu.name
        if menu.recipe:
            ingredients = ', '.join(
                ri.item.name for ri in menu.recipe.ingredients.all()[:8]
            )
            description = f"ส่วนผสมหลัก: {ingredients}"

    client = _get_anthropic_client()
    if client:
        try:
            prompt = f"""{BRAND_CONTEXT}

เมนูปัจจุบัน: {current_name}
{f'รายละเอียด: {description}' if description else ''}

ช่วยตั้งชื่อเมนูใหม่ 5 ชื่อ ตามแบรนด์ร้านสารข้าว:
- ชื่อต้องสื่อถึงอาหารใต้แท้จากตรัง
- ใช้ภาษาไทยที่สวย ดึงดูด แต่ไม่ยาวเกินไป
- อาจผสมคำถิ่นใต้ได้
- เหมาะสำหรับใช้ในเมนูร้านอาหาร

ตอบเป็น JSON array: [{{"name": "ชื่อ", "reason": "เหตุผลสั้นๆ"}}]
ตอบ JSON เท่านั้น ไม่ต้องมี markdown"""

            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=500,
                messages=[{'role': 'user', 'content': prompt}],
            )
            text = response.content[0].text.strip()
            suggestions = json.loads(text)
            return JsonResponse({'ok': True, 'suggestions': suggestions})
        except Exception as e:
            logger.error(f'AI name generation error: {e}')
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    else:
        # Demo mode
        suggestions = [
            {'name': f'{current_name} สูตรตรัง', 'reason': 'เพิ่มที่มาจากตรัง'},
            {'name': f'{current_name} ทะเลตรัง', 'reason': 'เน้นวัตถุดิบทะเลสด'},
            {'name': f'{current_name} พื้นบ้าน', 'reason': 'สื่อถึงสูตรดั้งเดิม'},
            {'name': f'{current_name} สารข้าว', 'reason': 'ผูกกับชื่อแบรนด์'},
            {'name': f'{current_name} ปักษ์ใต้แท้', 'reason': 'เน้นความเป็นอาหารใต้แท้'},
        ]
        return JsonResponse({'ok': True, 'suggestions': suggestions, 'demo': True})


@require_POST
def ai_generate_content(request):
    """Generate social media content for selected menus"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    data = json.loads(request.body)
    menu_ids = data.get('menu_ids', [])
    content_type = data.get('content_type', 'ig_post')  # ig_post, fb_post, story, description

    tenant = request.user.tenant
    menus = MenuItem.objects.filter(id__in=menu_ids, tenant=tenant).select_related('recipe')

    menu_info = []
    for m in menus:
        info = f"- {m.name}"
        if m.selling_price:
            info += f" (฿{m.selling_price})"
        if m.recipe:
            ingredients = ', '.join(ri.item.name for ri in m.recipe.ingredients.all()[:6])
            if ingredients:
                info += f" — วัตถุดิบ: {ingredients}"
        menu_info.append(info)

    menu_text = '\n'.join(menu_info)

    content_type_prompts = {
        'ig_post': 'เขียน Instagram caption สำหรับโพสต์เมนูอาหาร พร้อม hashtag ที่เกี่ยวข้อง ความยาว 100-200 คำ',
        'fb_post': 'เขียน Facebook post แนะนำเมนูอาหาร เน้นเล่าเรื่องราวและวัตถุดิบ ความยาว 150-300 คำ',
        'story': 'เขียนข้อความสั้นสำหรับ Instagram Story 1-3 ประโยค กระชับ ดึงดูด',
        'description': 'เขียนคำอธิบายเมนูสำหรับใส่ในเมนูร้าน ความยาว 1-2 ประโยค ต่อเมนู',
    }

    client = _get_anthropic_client()
    if client:
        try:
            prompt = f"""{BRAND_CONTEXT}

เมนูที่เลือก:
{menu_text}

{content_type_prompts.get(content_type, content_type_prompts['ig_post'])}

โทนเสียง: อบอุ่น ใกล้ชิด เป็นกันเอง ภูมิใจในวัตถุดิบท้องถิ่นจากตรัง
เขียนเป็นภาษาไทย"""

            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}],
            )
            content = response.content[0].text.strip()
            return JsonResponse({'ok': True, 'content': content})
        except Exception as e:
            logger.error(f'AI content generation error: {e}')
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    else:
        # Demo mode
        menu_names = ', '.join(m.name for m in menus)
        demo_content = {
            'ig_post': f'วันนี้มาแนะนำเมนูเด็ดจากครัวสารข้าว! {menu_names} ปรุงสดใหม่ทุกจาน วัตถุดิบคัดสรรจากทะเลตรัง สดทุกเช้า มากินกันนะคะ\n\n#สารข้าว #อาหารใต้ #ตรัง #อาหารทะเลสด #ParimaHotel #ร้านอาหารตรัง #อาหารใต้แท้',
            'fb_post': f'สวัสดีค่ะทุกคน วันนี้ครัวสารข้าวขอแนะนำ {menu_names} เมนูสูตรต้นตำรับจากตรัง ใช้วัตถุดิบสดจากทะเลตรัง ปรุงสดใหม่ทุกจาน รับรองอร่อยเหมือนกินที่บ้านค่ะ มาลิ้มลองกันได้ที่ Parima Hotel นะคะ',
            'story': f'{menu_names} สดจากทะเลตรัง วันนี้ต้องลอง!',
            'description': f'{menu_names} — สูตรต้นตำรับปักษ์ใต้ วัตถุดิบคัดสรรจากตรัง',
        }
        return JsonResponse({
            'ok': True,
            'content': demo_content.get(content_type, demo_content['ig_post']),
            'demo': True,
        })
