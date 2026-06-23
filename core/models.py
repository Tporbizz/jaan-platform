from django.conf import settings
from django.db import models


class Notification(models.Model):
    """ศูนย์แจ้งเตือนในระบบ — เก็บทุกเหตุการณ์อัตโนมัติ (ของใกล้หมด, สั่งซื้อ, P&L ฯลฯ)"""

    class Level(models.TextChoices):
        INFO = 'info', 'ข้อมูล'
        SUCCESS = 'success', 'สำเร็จ'
        WARNING = 'warning', 'เตือน'
        DANGER = 'danger', 'ด่วน'

    class Category(models.TextChoices):
        STOCK = 'stock', 'สต็อก'
        EXPIRY = 'expiry', 'ของใกล้หมดอายุ'
        REORDER = 'reorder', 'สั่งซื้ออัตโนมัติ'
        FINANCE = 'finance', 'การเงิน/P&L'
        SYSTEM = 'system', 'ระบบ'

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='notifications', verbose_name='ร้าน')
    level = models.CharField('ระดับ', max_length=10, choices=Level.choices, default=Level.INFO)
    category = models.CharField('หมวด', max_length=20, choices=Category.choices, default=Category.SYSTEM)
    title = models.CharField('หัวข้อ', max_length=200)
    message = models.TextField('รายละเอียด', blank=True)
    link = models.CharField('ลิงก์', max_length=300, blank=True, help_text='URL ภายในระบบที่เกี่ยวข้อง')
    is_read = models.BooleanField('อ่านแล้ว', default=False)
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'core_notification'
        verbose_name = 'การแจ้งเตือน'
        verbose_name_plural = 'การแจ้งเตือน'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"


class AuditLog(models.Model):
    """บันทึกการกระทำสำคัญ — ใครทำอะไรเมื่อไหร่ (ระบบความปลอดภัย 2027)"""

    tenant = models.ForeignKey('accounts.Tenant', on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True, verbose_name='ร้าน')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ผู้ใช้')
    action = models.CharField('การกระทำ', max_length=100, help_text='เช่น order.paid, po.created, stock.adjust')
    model_name = models.CharField('โมเดล', max_length=100, blank=True)
    object_id = models.CharField('รหัสอ้างอิง', max_length=50, blank=True)
    summary = models.CharField('สรุป', max_length=300, blank=True)
    created_at = models.DateTimeField('เวลา', auto_now_add=True)

    class Meta:
        db_table = 'core_auditlog'
        verbose_name = 'บันทึกการใช้งาน'
        verbose_name_plural = 'บันทึกการใช้งาน'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.user} @ {self.created_at:%Y-%m-%d %H:%M}"
