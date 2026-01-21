"""
로컬 개발 환경 설정
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']  # 로컬 개발 환경

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# 데이터베이스 설정 (로컬 PostgreSQL)
# docker-compose.dev.yml의 값과 일치
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'teamA_db',       # docker-compose.dev.yml과 동일
        'USER': 'teamA',          # docker-compose.dev.yml과 동일
        'PASSWORD': '2025',       # docker-compose.dev.yml과 동일
        'HOST': 'postgres',       # Docker 컨테이너 이름
        'PORT': '5432',
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
