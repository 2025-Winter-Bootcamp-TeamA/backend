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
    'django_celery_beat',  # 크롤링 작업을 위해 추가
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

# # 1. Celery 브로커 및 결과 저장소 설정 (로컬 도커 전용)
# # base.py의 RabbitMQ 설정을 무시하고 로컬 Redis를 사용하도록 강제합니다.
# CELERY_BROKER_URL = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'

# # 2. 캐시 설정 (로컬 도커 전용)
# # 외부 AWS 주소 접속을 차단하고 로컬 Redis 컨테이너를 바라보게 합니다.
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://redis:6379/0',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }