"""
ASGI 설정
비동기 서버에서 사용
"""

import os
from django.core.asgi import get_asgi_application

# Django 설정 모듈 지정
# Docker Compose에서 DJANGO_SETTINGS_MODULE 환경변수로 설정됨
# - 로컬 개발: config.settings.local
# - 프로덕션: config.settings.production
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_asgi_application()
