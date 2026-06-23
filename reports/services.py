"""
Reports Automation Services
===========================
ปิดยอด P&L รายเดือนอัตโนมัติ — รวมรายได้จากยอดขายรายวัน + ต้นทุนของเสีย + ค่าแรง
"""
from decimal import Decimal

from django.db.models import Sum

ZERO = Decimal('0')


def rollup_monthly_pl(tenant, month, year):
    """
    คำนวณ/อัปเดต MonthlyPL ของเดือนนั้นจากข้อมูลจริงในระบบ (idempotent)

    รายได้      : รวมจาก DailySalesRecord ของเดือน
    Food cost   : รวมจาก DailySalesRecord.food_cost_actual (ต้นทุนจริงที่ตัดสต็อก)
    ของเสีย     : รวมจาก WasteRecord.cost_impact
    ค่าแรง      : รวมจาก PayrollRecord.gross_pay (ถ้ามี)
    """
    from .models import DailySalesRecord, MonthlyPL
    from restaurant.models import WasteRecord
    from hr.models import PayrollRecord

    daily = DailySalesRecord.objects.filter(tenant=tenant, date__year=year, date__month=month)
    agg = daily.aggregate(
        dine_in=Sum('dine_in_revenue'),
        beverage=Sum('beverage_revenue'),
        bf=Sum('bf_revenue'),
        event=Sum('event_revenue'),
        total=Sum('total_revenue'),
        fc_actual=Sum('food_cost_actual'),
        fc_theo=Sum('food_cost_theoretical'),
    )

    waste = (
        WasteRecord.objects
        .filter(tenant=tenant, waste_date__year=year, waste_date__month=month)
        .aggregate(s=Sum('cost_impact'))['s'] or ZERO
    )

    labour = (
        PayrollRecord.objects
        .filter(employee__tenant=tenant, year=year, month=month)
        .aggregate(s=Sum('gross_pay'))['s'] or ZERO
    )

    pl, _ = MonthlyPL.objects.get_or_create(tenant=tenant, month=month, year=year)
    pl.dine_in_revenue = agg['dine_in'] or ZERO
    pl.beverage_revenue = agg['beverage'] or ZERO
    pl.bf_revenue = agg['bf'] or ZERO
    pl.event_revenue = agg['event'] or ZERO
    pl.total_revenue = agg['total'] or ZERO
    pl.food_cost_actual = agg['fc_actual'] or ZERO
    pl.food_cost_theoretical = agg['fc_theo'] or ZERO
    pl.waste_cost = waste
    pl.labour_cost = labour
    pl.calculate()  # คำนวณ gross/net profit + เปอร์เซ็นต์
    pl.save()
    return pl
