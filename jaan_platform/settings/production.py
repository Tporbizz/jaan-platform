"""
Jaan Platform — Production Settings
"""

import dj_database_url
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='.onrender.com', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()])  # noqa: F405

# --- Database: PostgreSQL จาก DATABASE_URL ---
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://localhost:5432/jaan_platform',
        conn_max_age=600,
    )
}

# --- Security ---
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- Static files: Whitenoise ---
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = config(  # noqa: F405
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
