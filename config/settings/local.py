"""
로컬 개발 환경 설정
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# 데이터베이스 설정 (로컬 PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='teamAdb'),
        'USER': config('DB_USER', default='teamA'),
        'PASSWORD': config('DB_PASSWORD', default='2025'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# 이메일 설정 (콘솔 백엔드)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 디버그 도구
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

# REST Framework 개발 설정
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += [
    'rest_framework.renderers.BrowsableAPIRenderer',
]
