"""
Jaan Platform — Development Settings
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# SQLite สำหรับ dev — ไม่ต้องติดตั้งอะไรเพิ่ม
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS — อนุญาตทุก origin ใน dev
CORS_ALLOW_ALL_ORIGINS = True

# Email — แสดงใน console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug Toolbar (ถ้าติดตั้ง)
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass
