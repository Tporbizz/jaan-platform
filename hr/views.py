import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Employee, ShiftSchedule


def shift_today(request):
    """กะวันนี้ — ใครเข้ากะอะไร (หน้าหลัก HR)"""
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.localdate()

    today_shifts = ShiftSchedule.objects.filter(
        employee__tenant=tenant, date=today,
    ).select_related('employee')

    employees = Employee.objects.filter(tenant=tenant, is_active=True)

    context = {
        'today_shifts': today_shifts,
        'employees': employees,
        'employee_count': employees.count(),
        'today': today,
    }
    return render(request, 'hr/shift_today.html', context)


def shift_calendar(request):
    """ตารางกะรายสัปดาห์"""
    if not request.user.is_authenticated:
        return redirect('login')
    tenant = request.user.tenant
    today = timezone.localdate()

    start = today - datetime.timedelta(days=today.weekday())  # Monday
    end = start + datetime.timedelta(days=6)

    employees = Employee.objects.filter(tenant=tenant, is_active=True)
    shifts = ShiftSchedule.objects.filter(
        employee__tenant=tenant, date__gte=start, date__lte=end,
    ).select_related('employee')

    days = [start + datetime.timedelta(days=i) for i in range(7)]
    grid = {}
    for emp in employees:
        grid[emp.id] = {'employee': emp, 'days': {}}
        for d in days:
            grid[emp.id]['days'][d] = None
    for shift in shifts:
        if shift.employee_id in grid:
            grid[shift.employee_id]['days'][shift.date] = shift

    context = {
        'grid': grid,
        'days': days,
        'shift_types': ShiftSchedule.ShiftType.choices,
    }
    return render(request, 'hr/shift_calendar.html', context)


@require_POST
def assign_shift(request):
    if not request.user.is_authenticated:
        return redirect('login')

    emp_id = request.POST.get('employee_id')
    date_str = request.POST.get('date')
    shift_type = request.POST.get('shift_type')

    employee = get_object_or_404(Employee, id=emp_id)
    ShiftSchedule.objects.update_or_create(
        employee=employee, date=date_str,
        defaults={'shift_type': shift_type},
    )
    return redirect('hr:shift_calendar')


def api_today_staff(request):
    """JSON API — staff ที่อยู่กะวันนี้ (สำหรับ POS/Kitchen ดึงไปใช้)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    tenant = request.user.tenant
    today = timezone.localdate()

    shifts = ShiftSchedule.objects.filter(
        employee__tenant=tenant, date=today,
    ).select_related('employee')

    # กรองเฉพาะ kitchen staff
    kitchen_positions = ('chef', 'sous_chef', 'cook')
    kitchen_staff = [
        {
            'id': s.employee.id,
            'name': s.employee.name,
            'position': s.employee.get_position_display(),
            'shift': s.get_shift_type_display(),
        }
        for s in shifts if s.employee.position in kitchen_positions
    ]
    all_staff = [
        {
            'id': s.employee.id,
            'name': s.employee.name,
            'position': s.employee.get_position_display(),
            'shift': s.get_shift_type_display(),
        }
        for s in shifts
    ]

    return JsonResponse({'kitchen': kitchen_staff, 'all': all_staff})
