from django.conf import settings
from django.db import models
from django.utils import timezone


class HotelConfig(models.Model):
    class PMSType(models.TextChoices):
        ADS = 'ads', 'ADS Hotel PMS'
        OPERA = 'opera', 'Oracle Opera'
        MANUAL = 'manual', 'Manual CSV'

    class SyncMethod(models.TextChoices):
        API = 'api', 'API Integration'
        CSV = 'csv', 'CSV Import'
        MANUAL = 'manual', 'Manual Entry'

    tenant = models.OneToOneField('accounts.Tenant', on_delete=models.CASCADE, related_name='hotel_config')
    pms_type = models.CharField(max_length=20, choices=PMSType.choices, default=PMSType.ADS)
    api_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    sync_method = models.CharField(max_length=20, choices=SyncMethod.choices, default=SyncMethod.MANUAL)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'hotel_config'

    def __str__(self):
        return f"Hotel Config — {self.get_pms_type_display()}"


class GuestList(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='guest_list')
    room_number = models.CharField(max_length=10)
    guest_name = models.CharField(max_length=200)
    checkout_date = models.DateField()
    package_type = models.CharField(max_length=50, blank=True, help_text='เช่น RO, BB, HB, FB')
    bf_included = models.BooleanField(default=False)
    fb_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    import_date = models.DateField(default=timezone.now)

    class Meta:
        db_table = 'hotel_guestlist'
        ordering = ['room_number']

    def __str__(self):
        return f"Room {self.room_number} — {self.guest_name}"


class RoomCharge(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'รอ FO อนุมัติ'
        POSTED = 'posted', 'โพสต์แล้ว'
        REJECTED = 'rejected', 'ถูกปฏิเสธ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='room_charges')
    room_number = models.CharField(max_length=10)
    guest_name = models.CharField(max_length=200)
    order = models.ForeignKey('pos.Order', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hotel_roomcharge'
        ordering = ['-created_at']

    def __str__(self):
        return f"Room {self.room_number} — ฿{self.amount}"


class BFSettlement(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='bf_settlements')
    date = models.DateField()
    total_covers = models.PositiveIntegerField(default=0)
    bb_covers = models.PositiveIntegerField(default=0, help_text='Bed & Breakfast')
    hb_covers = models.PositiveIntegerField(default=0, help_text='Half Board')
    fb_covers = models.PositiveIntegerField(default=0, help_text='Full Board')
    walkin_covers = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'hotel_bfsettlement'
        unique_together = ['tenant', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"BF {self.date} — {self.total_covers} covers"
