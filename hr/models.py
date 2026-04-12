from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


class Employee(models.Model):
    class Position(models.TextChoices):
        CHEF = 'chef', 'เชฟ/พ่อครัว'
        SOUS_CHEF = 'sous_chef', 'ผู้ช่วยเชฟ'
        COOK = 'cook', 'แม่ครัว/คนครั��'
        SERVER = 'server', 'พนักงานเสิร์ฟ'
        CASHIER = 'cashier', 'แคชเชียร์'
        MANAGER = 'manager', 'ผู้จัดการ'
        CLEANER = 'cleaner', 'แม่บ้าน'
        OTHER = 'other', 'อื่นๆ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='employees')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=20, choices=Position.choices, default=Position.SERVER)
    phone = models.CharField(max_length=20, blank=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ot_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    start_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'hr_employee'
        ordering = ['first_name']

    @property
    def name(self):
        if self.nickname:
            return self.nickname
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def monthly_salary(self):
        return self.base_salary

    @property
    def daily_rate(self):
        return self.hourly_rate * 8 if self.hourly_rate else None

    def __str__(self):
        return f"{self.name} ({self.get_position_display()})"


class ShiftSchedule(models.Model):
    class ShiftType(models.TextChoices):
        MORNING = 'morning', 'เช้า (06:00-14:00)'
        EVENING = 'evening', 'บ่าย (14:00-22:00)'
        SPLIT = 'split', 'สปลิท (10:00-14:00, 17:00-21:00)'
        FULL = 'full', 'เต็มวัน (08:00-20:00)'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='shifts')
    date = models.DateField()
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'hr_shiftschedule'
        unique_together = ['employee', 'date']
        ordering = ['date', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.date} {self.get_shift_type_display()}"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ot_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'hr_attendance'
        unique_together = ['employee', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} — {self.date}"

    def calculate_hours(self):
        if self.clock_in and self.clock_out:
            from datetime import datetime, timedelta
            dt_in = datetime.combine(self.date, self.clock_in)
            dt_out = datetime.combine(self.date, self.clock_out)
            if dt_out < dt_in:
                dt_out += timedelta(days=1)
            total = (dt_out - dt_in).total_seconds() / 3600
            self.total_hours = Decimal(str(round(total, 2)))
            self.ot_hours = max(self.total_hours - Decimal('8'), Decimal('0'))


class PayrollRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ot_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sso_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='ประกันสังคม 5%')
    tax_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    days_worked = models.PositiveIntegerField(default=0)
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    ot_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'hr_payroll'
        unique_together = ['employee', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee} — {self.month}/{self.year} ฿{self.net_pay}"

    def calculate(self):
        # Sum attendance hours
        attendance = Attendance.objects.filter(
            employee=self.employee,
            date__year=self.year, date__month=self.month,
        )
        self.days_worked = attendance.count()
        self.regular_hours = sum(min(a.total_hours, Decimal('8')) for a in attendance)
        self.ot_hours = sum(a.ot_hours for a in attendance)

        self.base_pay = self.employee.base_salary
        self.ot_pay = self.ot_hours * self.employee.ot_rate
        self.gross_pay = self.base_pay + self.ot_pay + self.bonus

        # SSO 5% (max 750)
        self.sso_deduction = min(self.gross_pay * Decimal('0.05'), Decimal('750'))
        self.net_pay = self.gross_pay - self.sso_deduction - self.tax_deduction - self.other_deduction
