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

    tenant = models.OneToOneField('accounts.Tenant', on_delete=models.CASCADE, related_name='hotel_config', verbose_name='ร้าน')
    pms_type = models.CharField('ประเภท PMS', max_length=20, choices=PMSType.choices, default=PMSType.ADS)
    api_url = models.URLField('API URL', blank=True)
    api_key = models.CharField('API Key', max_length=200, blank=True)
    sync_method = models.CharField('วิธี Sync', max_length=20, choices=SyncMethod.choices, default=SyncMethod.MANUAL)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)

    class Meta:
        db_table = 'hotel_config'
        verbose_name = 'ตั้งค่าโรงแรม'
        verbose_name_plural = 'ตั้งค่าโรงแรม'

    def __str__(self):
        return f"Hotel Config — {self.get_pms_type_display()}"


class GuestList(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='guest_list', verbose_name='ร้าน')
    room_number = models.CharField('เลขห้อง', max_length=10)
    guest_name = models.CharField('ชื่อแขก', max_length=200)
    checkout_date = models.DateField('วันเช็คเอาต์')
    package_type = models.CharField('ประเภทแพ็กเกจ', max_length=50, blank=True, help_text='เช่น RO, BB, HB, FB')
    bf_included = models.BooleanField('รวมอาหารเช้า', default=False)
    fb_balance = models.DecimalField('วงเงิน F&B', max_digits=10, decimal_places=2, default=0)
    import_date = models.DateField('วันที่นำเข้า', default=timezone.now)

    class Meta:
        db_table = 'hotel_guestlist'
        verbose_name = 'รายชื่อแขก'
        verbose_name_plural = 'รายชื่อแขก'
        ordering = ['room_number']

    def __str__(self):
        return f"Room {self.room_number} — {self.guest_name}"


class RoomCharge(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'รอ FO อนุมัติ'
        POSTED = 'posted', 'โพสต์แล้ว'
        REJECTED = 'rejected', 'ถูกปฏิเสธ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='room_charges', verbose_name='ร้าน')
    room_number = models.CharField('เลขห้อง', max_length=10)
    guest_name = models.CharField('ชื่อแขก', max_length=200)
    order = models.ForeignKey('pos.Order', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ออเดอร์')
    amount = models.DecimalField('จำนวนเงิน', max_digits=10, decimal_places=2)
    status = models.CharField('สถานะ', max_length=20, choices=Status.choices, default=Status.PENDING)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='โพสต์โดย')
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'hotel_roomcharge'
        verbose_name = 'เซ็นห้อง'
        verbose_name_plural = 'เซ็นห้อง'
        ordering = ['-created_at']

    def __str__(self):
        return f"Room {self.room_number} — ฿{self.amount}"


class BFSettlement(models.Model):
    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='bf_settlements', verbose_name='ร้าน')
    date = models.DateField('วันที่')
    total_covers = models.PositiveIntegerField('จำนวน Covers รวม', default=0)
    bb_covers = models.PositiveIntegerField('BB Covers', default=0, help_text='Bed & Breakfast')
    hb_covers = models.PositiveIntegerField('HB Covers', default=0, help_text='Half Board')
    fb_covers = models.PositiveIntegerField('FB Covers', default=0, help_text='Full Board')
    walkin_covers = models.PositiveIntegerField('Walk-in Covers', default=0)
    total_amount = models.DecimalField('ยอดรวม', max_digits=12, decimal_places=2, default=0)
    approved = models.BooleanField('อนุมัติแล้ว', default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='อนุมัติโดย')
    notes = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        db_table = 'hotel_bfsettlement'
        verbose_name = 'สรุปอาหารเช้า'
        verbose_name_plural = 'สรุปอาหารเช้า'
        unique_together = ['tenant', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"BF {self.date} — {self.total_covers} covers"
