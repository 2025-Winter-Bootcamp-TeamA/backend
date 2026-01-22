# apps/jobs/tasks.py

from celery import shared_task
from django.core.management import call_command

@shared_task
def schedule_crawling():
    """
    [Celery Beat] 주기적 크롤링 작업
    """
    print("[Celery] 정기 크롤링 작업을 시작합니다...")
    
    # 아까 만든 커스텀 명령어 실행 (command 이름이 'run_crawling')
    # count=50 옵션을 줘서 50개씩만 수집하도록 설정
    call_command('run_crawling', count=50) 
    print("[Celery] 크롤링 작업 완료!")