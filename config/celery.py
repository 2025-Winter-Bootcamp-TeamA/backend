"""
Celery 비동기 작업 설정
트렌드 데이터 수집, 이력서 분석 등 백그라운드 작업 처리
"""

import os
from celery import Celery

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Celery 앱 생성
app = Celery('teamA')

# Django 설정에서 Celery 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱에서 tasks.py 자동 검색
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """디버그용 테스트 태스크"""
    print(f'Request: {self.request!r}')
