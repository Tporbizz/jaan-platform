from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """ร้านอาหาร 1 ร้าน = 1 Tenant — ใช้แยกข้อมูลระหว่างร้าน"""

    name = models.CharField('ชื่อร้าน', max_length=200)
    slug = models.SlugField('slug', max_length=100, unique=True)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)
    created_at = models.DateTimeField('สร้างเมื่อ', auto_now_add=True)

    class Meta:
        db_table = 'accounts_tenant'
        verbose_name = 'ร้าน'
        verbose_name_plural = 'ร้าน'

    def __str__(self):
        return self.name


class RestaurantBranch(models.Model):
    """สาขาของร้าน — 1 Tenant มีได้หลายสาขา"""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='branches', verbose_name='ร้าน')
    name = models.CharField('ชื่อสาขา', max_length=200)
    address = models.TextField('ที่อยู่', blank=True)
    phone = models.CharField('โทรศัพท์', max_length=20, blank=True)
    is_active = models.BooleanField('เปิดใช้งาน', default=True)

    class Meta:
        db_table = 'accounts_branch'
        verbose_name = 'สาขา'
        verbose_name_plural = 'สาขา'

    def __str__(self):
        return f"{self.tenant.name} — {self.name}"


class User(AbstractUser):
    """Custom User model พร้อม multi-tenant + role-based access"""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        STAFF = 'staff', 'Staff'
        READONLY = 'readonly', 'Read Only'

    class Department(models.TextChoices):
        GM = 'gm', 'GM / Owner'
        MANAGER = 'manager', 'Manager'
        FB = 'fb', 'FB (หน้าร้าน/บาร์)'
        KT = 'kt', 'KT (ครัว)'

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='users', null=True, blank=True,
        verbose_name='ร้าน',
    )
    role = models.CharField(
        'บทบาท', max_length=20, choices=Role.choices, default=Role.STAFF,
    )
    department = models.CharField(
        'แผนก', max_length=10, choices=Department.choices, default=Department.FB,
        help_text='แผนกที่สังกัด — กำหนดหน้าที่เข้าถึงได้',
    )
    restaurant_branch = models.ForeignKey(
        RestaurantBranch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff',
        verbose_name='สาขา',
    )
    phone = models.CharField('โทรศัพท์', max_length=20, blank=True)
    avatar = models.ImageField('รูปโปรไฟล์', upload_to='avatars/', blank=True)

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'ผู้ใช้งาน'
        verbose_name_plural = 'ผู้ใช้งาน'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_manager(self):
        return self.role in (self.Role.OWNER, self.Role.MANAGER)

    @property
    def is_staff_role(self):
        return self.role in (self.Role.OWNER, self.Role.MANAGER, self.Role.STAFF)

    @property
    def is_gm(self):
        return self.department == self.Department.GM or self.role == self.Role.OWNER

    @property
    def is_kitchen(self):
        return self.department == self.Department.KT

    @property
    def is_fb(self):
        return self.department == self.Department.FB

    @property
    def can_access_pos(self):
        """FB, Manager, GM สามารถเข้า POS ได้"""
        return self.department in (self.Department.FB, self.Department.MANAGER, self.Department.GM) or self.is_manager

    @property
    def can_access_kitchen(self):
        """KT, Manager, GM สามารถเข้า Kitchen Display ได้"""
        return self.department in (self.Department.KT, self.Department.MANAGER, self.Department.GM) or self.is_manager

    @property
    def can_access_stock(self):
        """Manager, GM เข้าถึง Stock/Reports"""
        return self.department in (self.Department.MANAGER, self.Department.GM) or self.is_manager

    @property
    def can_access_settings(self):
        """GM เท่านั้นเข้าถึง Settings, P&L, Food Cost"""
        return self.is_gm or self.role == self.Role.OWNER
