import csv
import io

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import BFSettlement, GuestList, HotelConfig, RoomCharge


def hotel_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.now().date()

    config = HotelConfig.objects.filter(tenant=tenant).first()
    guests = GuestList.objects.filter(tenant=tenant, checkout_date__gte=today)
    pending_charges = RoomCharge.objects.filter(tenant=tenant, status='pending')
    recent_settlements = BFSettlement.objects.filter(tenant=tenant)[:7]

    context = {
        'config': config,
        'guests': guests,
        'guest_count': guests.count(),
        'pending_charges': pending_charges,
        'pending_count': pending_charges.count(),
        'recent_settlements': recent_settlements,
    }
    return render(request, 'hotel/hotel_dashboard.html', context)


def room_lookup(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    tenant = request.user.tenant
    room = request.GET.get('room', '').strip()

    if not room:
        return JsonResponse({'error': 'No room number'}, status=400)

    guest = GuestList.objects.filter(
        tenant=tenant, room_number=room, checkout_date__gte=timezone.now().date(),
    ).first()

    if not guest:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'guest_name': guest.guest_name,
        'room_number': guest.room_number,
        'checkout_date': str(guest.checkout_date),
        'package_type': guest.package_type,
        'bf_included': guest.bf_included,
        'fb_balance': str(guest.fb_balance),
    })


@require_POST
def import_guest_csv(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return redirect('hotel_integration:hotel_dashboard')

    decoded = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))

    count = 0
    today = timezone.now().date()
    for row in reader:
        room = row.get('room', row.get('Room', '')).strip()
        name = row.get('guest_name', row.get('Guest Name', row.get('name', ''))).strip()
        checkout = row.get('checkout', row.get('Checkout', '')).strip()
        pkg = row.get('package', row.get('Package', '')).strip()

        if not room or not name:
            continue

        GuestList.objects.update_or_create(
            tenant=tenant, room_number=room, import_date=today,
            defaults={
                'guest_name': name,
                'checkout_date': checkout or today,
                'package_type': pkg,
                'bf_included': pkg.upper() in ('BB', 'HB', 'FB'),
            },
        )
        count += 1

    return redirect('hotel_integration:hotel_dashboard')


@require_POST
def post_room_charge(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    tenant = request.user.tenant

    room = request.POST.get('room_number', '')
    guest_name = request.POST.get('guest_name', '')
    amount = request.POST.get('amount', '0')

    charge = RoomCharge.objects.create(
        tenant=tenant, room_number=room, guest_name=guest_name,
        amount=amount, posted_by=request.user,
    )
    return JsonResponse({'ok': True, 'id': charge.id})


def bf_settlement(request):
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.now().date()

    if request.method == 'POST':
        date = request.POST.get('date', str(today))
        BFSettlement.objects.update_or_create(
            tenant=tenant, date=date,
            defaults={
                'total_covers': int(request.POST.get('total_covers', 0)),
                'bb_covers': int(request.POST.get('bb_covers', 0)),
                'hb_covers': int(request.POST.get('hb_covers', 0)),
                'fb_covers': int(request.POST.get('fb_covers', 0)),
                'walkin_covers': int(request.POST.get('walkin_covers', 0)),
                'total_amount': request.POST.get('total_amount', 0),
            },
        )
        return redirect('hotel_integration:bf_settlement')

    settlements = BFSettlement.objects.filter(tenant=tenant)[:30]
    return render(request, 'hotel/bf_settlement.html', {'settlements': settlements, 'today': today})
