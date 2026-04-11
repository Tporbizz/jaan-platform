from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """ร้านอาหาร 1 ร้าน = 1 Tenant — ใช้แยกข้อมูลระหว่างร้าน"""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_tenant'

    def __str__(self):
        return self.name


class RestaurantBranch(models.Model):
    """สาขาของร้าน — 1 Tenant มีได้หลายสาขา"""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'accounts_branch'
        verbose_name_plural = 'Restaurant branches'

    def __str__(self):
        return f"{self.tenant.name} — {self.name}"


class User(AbstractUser):
    """Custom User model พร้อม multi-tenant + role-based access"""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        STAFF = 'staff', 'Staff'
        READONLY = 'readonly', 'Read Only'

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='users', null=True, blank=True,
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STAFF,
    )
    restaurant_branch = models.ForeignKey(
        RestaurantBranch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff',
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    class Meta:
        db_table = 'accounts_user'

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
