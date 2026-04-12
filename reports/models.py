from django.conf import settings
from django.db import models
from django.utils import timezone


class DailySalesRecord(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='daily_sales', verbose_name='ร้าน')
    date = models.DateField('วันที่')
    dine_in_revenue = models.DecimalField('รายได้ Dine-in', max_digits=12, decimal_places=2, default=0)
    beverage_revenue = models.DecimalField('รายได้เครื่องดื่ม', max_digits=12, decimal_places=2, default=0)
    bf_revenue = models.DecimalField('รายได้อาหารเช้า', max_digits=12, decimal_places=2, default=0)
    event_revenue = models.DecimalField('รายได้อีเวนต์', max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField('รายได้รวม', max_digits=12, decimal_places=2, default=0)
    total_covers = models.PositiveIntegerField('จำนวน Covers', default=0)
    avg_check = models.DecimalField('เฉลี่ยต่อคน', max_digits=10, decimal_places=2, default=0)
    food_cost_actual = models.DecimalField('Food Cost จริง', max_digits=12, decimal_places=2, default=0)
    food_cost_theoretical = models.DecimalField('Food Cost ทฤษฎี', max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_dailysales'
        verbose_name = 'ยอดขายรายวัน'
        verbose_name_plural = 'ยอดขายรายวัน'
        unique_together = ['tenant', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Sales {self.date} — ฿{self.total_revenue}"


class MonthlyPL(models.Model):
    """Monthly Profit & Loss snapshot"""
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='monthly_pl', verbose_name='ร้าน')
    month = models.PositiveIntegerField('เดือน')
    year = models.PositiveIntegerField('ปี')

    # Revenue
    dine_in_revenue = models.DecimalField('รายได้ Dine-in', max_digits=12, decimal_places=2, default=0)
    beverage_revenue = models.DecimalField('รายได้เครื่องดื่ม', max_digits=12, decimal_places=2, default=0)
    bf_revenue = models.DecimalField('รายได้อาหารเช้า', max_digits=12, decimal_places=2, default=0)
    event_revenue = models.DecimalField('รายได้อีเวนต์', max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField('รายได้รวม', max_digits=12, decimal_places=2, default=0)

    # COGS
    food_cost_theoretical = models.DecimalField('Food Cost ทฤษฎี', max_digits=12, decimal_places=2, default=0)
    food_cost_actual = models.DecimalField('Food Cost จริง', max_digits=12, decimal_places=2, default=0)
    waste_cost = models.DecimalField('ต้นทุนของเสีย', max_digits=12, decimal_places=2, default=0)
    variance_cost = models.DecimalField('ส่วนต่าง Food Cost', max_digits=12, decimal_places=2, default=0)

    # OpEx
    labour_cost = models.DecimalField('ต้นทุนแรงงาน', max_digits=12, decimal_places=2, default=0)
    electricity_cost = models.DecimalField('ค่าไฟ', max_digits=12, decimal_places=2, default=0)
    other_expenses = models.DecimalField('ค่าใช้จ่ายอื่นๆ', max_digits=12, decimal_places=2, default=0)

    # Calculated
    gross_profit = models.DecimalField('กำไรขั้นต้น', max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField('กำไรสุทธิ', max_digits=12, decimal_places=2, default=0)
    food_cost_pct = models.DecimalField('Food Cost %', max_digits=5, decimal_places=2, default=0)
    labour_cost_pct = models.DecimalField('Labour Cost %', max_digits=5, decimal_places=2, default=0)
    prime_cost_pct = models.DecimalField('Prime Cost %', max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_monthlypl'
        verbose_name = 'P&L รายเดือน'
        verbose_name_plural = 'P&L รายเดือน'
        unique_together = ['tenant', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"P&L {self.month}/{self.year}"

    def calculate(self):
        cogs = self.food_cost_actual + self.waste_cost
        opex = self.labour_cost + self.electricity_cost + self.other_expenses
        self.gross_profit = self.total_revenue - cogs
        self.net_profit = self.gross_profit - opex
        if self.total_revenue:
            self.food_cost_pct = (self.food_cost_actual / self.total_revenue) * 100
            self.labour_cost_pct = (self.labour_cost / self.total_revenue) * 100
            self.prime_cost_pct = self.food_cost_pct + self.labour_cost_pct
        self.variance_cost = self.food_cost_actual - self.food_cost_theoretical


class ACUsageLog(models.Model):
    """Sensibo AC usage tracking — Phase 8"""
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='ac_logs', verbose_name='ร้าน')
    device_id = models.CharField('Device ID', max_length=50)
    timestamp = models.DateTimeField('เวลา')
    power_watts = models.DecimalField('กำลังไฟ (W)', max_digits=8, decimal_places=2, default=0)
    temperature = models.DecimalField('อุณหภูมิ', max_digits=4, decimal_places=1, default=0)
    humidity = models.DecimalField('ความชื้น', max_digits=4, decimal_places=1, default=0)
    ac_on = models.BooleanField('เปิดแอร์', default=False)
    estimated_cost_thb = models.DecimalField('ค่าไฟโดยประมาณ (บาท)', max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_acusagelog'
        verbose_name = 'บันทึกการใช้แอร์'
        verbose_name_plural = 'บันทึกการใช้แอร์'
        ordering = ['-timestamp']

    def __str__(self):
        return f"AC {self.device_id} — {self.power_watts}W ({self.timestamp})"
