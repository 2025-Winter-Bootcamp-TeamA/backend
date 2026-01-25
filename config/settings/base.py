"""
Django 기본 설정 파일
모든 환경에서 공통으로 사용되는 설정
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import Config, RepositoryEnv
from celery.schedules import crontab #셀러리비트 스케쥴

# 프로젝트 기본 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 환경에 따라 적절한 .env 파일 로드
# DJANGO_SETTINGS_MODULE 환경변수를 확인하여 어떤 .env 파일을 사용할지 결정
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
if 'production' in settings_module:
    env_file = BASE_DIR / '.env.production'
elif 'local' in settings_module:
    env_file = BASE_DIR / '.env.local'
else:
    # 기본값: .env 파일 사용
    env_file = BASE_DIR / '.env'

# .env 파일이 존재하면 명시적으로 로드
if env_file.exists():
    config = Config(RepositoryEnv(str(env_file)))
else:
    # .env 파일이 없으면 시스템 환경변수에서만 읽기
    from decouple import config

# 보안 키 (환경변수에서 로드, 필수값)
SECRET_KEY = config('SECRET_KEY')

# 설치된 앱
INSTALLED_APPS = [
    # Django 기본 앱
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # 소셜 로그인용

    # 서드파티 앱
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_yasg',
    'django_celery_beat',  # 크롤링 작업을 위해 추가
    'django_prometheus',  # 모니터링 용
    # # 소셜 로그인 우린 allauth가아닌 requests 라이브러리 +  SimpleJWT 사용
    # 'allauth',
    # 'allauth.account',
    # 'allauth.socialaccount',
    # 'allauth.socialaccount.providers.google',

    # AWS S3 연동을 위한 라이브러리
    'storages',

    # 프로젝트 앱
    'apps.users',
    'apps.trends',
    'apps.jobs',
    'apps.resumes',
    'apps.interviews',

    'apps.analytics'
]

# 미들웨어
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    #'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 비밀번호 검증
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 국제화 설정
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# 정적 파일 설정
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# 미디어 파일 설정 (기본값)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 기본 PK 필드 타입
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 소셜 로그인 사이트 ID
SITE_ID = 1

# 사용자 정의 User 모델
AUTH_USER_MODEL = 'users.User'

# 소셜 로그인 인증 백엔드
# allauth는 사용하지 않으므로 ModelBackend만 사용
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    # 'allauth.account.auth_backends.AuthenticationBackend',  # allauth 미사용
]

# Django REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# JWT 설정
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==========================================
# Celery 설정 (보안 강화: 동적 조립)
# ==========================================
# 환경 변수에서 재료를 각각 가져옵니다.
MQ_USER = config('RABBITMQ_USER')
MQ_PASS = config('RABBITMQ_PASSWORD')
MQ_HOST = config('RABBITMQ_HOST')
MQ_PORT = config('RABBITMQ_PORT')

# 가져온 재료로 접속 주소를 조립합니다.
CELERY_BROKER_URL = f"amqp://{MQ_USER}:{MQ_PASS}@{MQ_HOST}:{MQ_PORT}//"

CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30분

# Celery Beat 스케줄 설정
CELERY_BEAT_SCHEDULE = {
    # 1. 크롤링 (매일 밤 23:00)
    'daily-crawling': {
        'task': 'apps.jobs.tasks.schedule_crawling',
        'schedule': crontab(hour=23, minute=0),
    },
    
    # 2. 트렌드 집계 (매일 밤 23:30) - 크롤링 끝나고 50분 뒤
    'daily-trend-calculation': {
        'task': 'apps.jobs.tasks.calculate_daily_trends',
        'schedule': crontab(hour=23, minute=50),
    },
}

# 캐시 설정 (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==========================================
# AWS S3 설정 (이미지/파일 업로드용)
# ==========================================
# 1. AWS 접속 정보 (비밀번호는 .env에서 가져옵니다!)
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME')

# 2. AWS S3 접속 설정
# 버킷 이름이 설정되어 있을 때만 S3를 사용합니다.
if AWS_STORAGE_BUCKET_NAME:
    # 파일 덮어쓰기 방지 (같은 이름의 파일이 올라오면 이름 뒤에 난수 생성)
    AWS_S3_FILE_OVERWRITE = False
    
    # 이미지를 누구나 볼 수 있게 서명 기능 끄기 (공개 버킷이므로)
    AWS_QUERYSTRING_AUTH = False 
    
    # 업로드된 파일을 누구나 읽을 수 있게 설정 (중요!)
    AWS_DEFAULT_ACL = 'public-read'
    
    # 미디어 파일(이미지 등)을 S3에 저장하는 도구 연결
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # S3 이미지 주소 자동 생성 (https://버킷이름.s3.amazonaws.com/...)
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

# AI API 키 설정
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
GOOGLE_GEMINI_API_KEY = config('GOOGLE_GEMINI_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Swagger (drf-yasg) 설정
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT "Bearer <token>"'
        }
    },
    'USE_SESSION_AUTH': False,
}

# OLLAMA 설정
OLLAMA_URL = config('OLLAMA_URL')

# Oauth
GOOGLE_OAUTH2_CLIENT_ID = config('GOOGLE_OAUTH2_CLIENT_ID', default='')
GOOGLE_OAUTH2_CLIENT_SECRET = config('GOOGLE_OAUTH2_CLIENT_SECRET', default='')
GOOGLE_REDIRECT_URI = config('GOOGLE_REDIRECT_URI', default='')
