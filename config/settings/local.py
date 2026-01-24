"""
로컬 개발 환경 설정
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'backend']  # 로컬 개발 환경

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# 데이터베이스 설정 (.env에서 로드)
# 로컬 개발 시에도 .env의 설정을 사용합니다
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
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
    'localhost',
]  # Django Debug Toolbar 표시 IP

# REST Framework 개발 설정
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += [
    'rest_framework.renderers.BrowsableAPIRenderer',
]
