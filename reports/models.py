from django.conf import settings
from django.db import models
from django.utils import timezone


class DailySalesRecord(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='daily_sales')
    date = models.DateField()
    dine_in_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    beverage_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bf_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    event_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_covers = models.PositiveIntegerField(default=0)
    avg_check = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_cost_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food_cost_theoretical = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_dailysales'
        unique_together = ['tenant', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Sales {self.date} — ฿{self.total_revenue}"


class MonthlyPL(models.Model):
    """Monthly Profit & Loss snapshot"""
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='monthly_pl')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()

    # Revenue
    dine_in_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    beverage_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bf_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    event_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # COGS
    food_cost_theoretical = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food_cost_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    waste_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    variance_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # OpEx
    labour_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    electricity_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Calculated
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food_cost_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    labour_cost_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    prime_cost_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_monthlypl'
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
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='ac_logs')
    device_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    power_watts = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    humidity = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    ac_on = models.BooleanField(default=False)
    estimated_cost_thb = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = 'reports_acusagelog'
        ordering = ['-timestamp']

    def __str__(self):
        return f"AC {self.device_id} — {self.power_watts}W ({self.timestamp})"
