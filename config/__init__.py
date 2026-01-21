# TeamA Backend 설정 패키지
from .celery import app as celery_app

__all__ = ('celery_app',)