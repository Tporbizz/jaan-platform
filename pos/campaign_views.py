"""
Sales Campaign Views — กระดานเชียร์ขาย + ตั้งเป้า/ค่าคอม
ดีไซน์: ตัวหนังสือใหญ่ อ่านง่ายบนมือถือ ไม่ใช้ emoji เน้นดูโปร
"""
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import require_pos
from restaurant.models import MenuItem
from .models import SalesCampaign, CampaignItem
from .services import get_active_campaign, campaign_progress


@require_pos
def campaign_board(request):
    """กระดานเชียร์ขายวันนี้ — ความคืบหน้าทีม + กระดานผู้นำ + ยอดของฉัน"""
    tenant = request.user.tenant
    campaign = get_active_campaign(tenant)

    data = campaign_progress(campaign) if campaign else None
    my_name = request.user.get_full_name() or request.user.username

    return render(request, 'pos/campaign_board.html', {
        'campaign': campaign,
        'data': data,
        'my_name': my_name,
        'can_edit': request.user.is_manager,
        'today': timezone.localdate(),
    })


@require_pos
def campaign_edit(request):
    """ตั้งเป้าเชียร์ขายวันนี้ — ผู้จัดการเลือกเมนูกำไรดี ตั้งเป้าทีม + ค่าคอมต่อจาน"""
    tenant = request.user.tenant
    if not request.user.is_manager:
        messages.error(request, 'เฉพาะผู้จัดการเท่านั้นที่ตั้งเป้าได้')
        return redirect('pos:campaign_board')

    today = timezone.localdate()
    campaign = get_active_campaign(tenant, today)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or 'เป้าเชียร์ขายวันนี้'
        note = request.POST.get('note', '').strip()

        if not campaign:
            campaign = SalesCampaign.objects.create(
                tenant=tenant, date=today, title=title, note=note,
                created_by=request.user,
            )
        else:
            campaign.title = title
            campaign.note = note
            campaign.save()

        # อ่านเมนูที่เลือก: target_<menuid>, comm_<menuid>
        campaign.items.all().delete()
        for menu in MenuItem.objects.filter(tenant=tenant):
            try:
                target = int(request.POST.get(f'target_{menu.id}', 0) or 0)
            except ValueError:
                target = 0
            if target <= 0:
                continue
            try:
                comm = Decimal(request.POST.get(f'comm_{menu.id}', '0') or '0')
            except (ValueError, ArithmeticError):
                comm = Decimal('0')
            CampaignItem.objects.create(
                campaign=campaign, menu_item=menu,
                target_qty=target, commission_per_dish=comm,
            )

        messages.success(request, 'บันทึกเป้าเชียร์ขายแล้ว')
        return redirect('pos:campaign_board')

    # GET — รายการเมนู พร้อมแนะนำเมนูกำไรดี (food cost <= 35%) ขึ้นก่อน
    menus = MenuItem.objects.filter(
        tenant=tenant, is_available=True,
    ).select_related('recipe').order_by('menu_category', 'name')

    existing = {}
    if campaign:
        existing = {ci.menu_item_id: ci for ci in campaign.items.all()}

    menu_rows = []
    for m in menus:
        fc = m.food_cost_pct
        ci = existing.get(m.id)
        menu_rows.append({
            'menu': m,
            'fc_pct': fc,
            'is_high_margin': bool(fc and fc <= 35),
            'target': ci.target_qty if ci else '',
            'commission': ci.commission_per_dish if ci else '',
        })
    # เมนูกำไรดีขึ้นก่อน
    menu_rows.sort(key=lambda r: (not r['is_high_margin'], r['menu'].name))

    return render(request, 'pos/campaign_edit.html', {
        'campaign': campaign,
        'menu_rows': menu_rows,
        'today': today,
    })
