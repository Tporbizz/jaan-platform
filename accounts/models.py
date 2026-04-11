from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model สำหรับ Jaan Platform
    จะเพิ่ม fields เพิ่มเติมใน Phase 0.2 (tenant, role, branch, phone, avatar)
    """

    class Meta:
        db_table = 'accounts_user'
