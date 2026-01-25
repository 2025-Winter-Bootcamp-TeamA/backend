# apps/jobs/tasks.py

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from apps.jobs.models import TechStack, JobPosting
from apps.trends.models import TechTrend # 모델 경로 확인 필요
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

@shared_task
def calculate_daily_trends():
    """
    [Celery] 일별 트렌드 집계 (채용공고 기준)
    """
    now = timezone.now()
    today = now.date()
    
    print(f"[Trend] {today} 일자 기술 트렌드 집계 시작...")

    stacks = TechStack.objects.all()
    
    for stack in stacks:
        # 1. 채용 공고 카운트
        current_job_count = stack.job_postings.filter(
            is_deleted=False,
            job_posting__is_deleted=False
        ).count()

        # 2. 전주 데이터 가져오기 (7일 전)
        target_date = today - timedelta(days=7)
        
        last_trend = TechTrend.objects.filter(
            tech_stack=stack,
            reference_date=target_date
        ).first()

        prev_job_count = last_trend.job_mention_count if last_trend else 0
        
        # 3. 채용 공고 증가율(%) 계산
        job_change_rate = 0.0
        if prev_job_count > 0:
            job_change_rate = ((current_job_count - prev_job_count) / prev_job_count) * 100
            
        # 4. 데이터 저장 (trend_from 삭제됨, 필드명 변경 반영)
        TechTrend.objects.update_or_create(
            tech_stack=stack,
            reference_date=today,
            defaults={
                'job_mention_count': current_job_count,
                'job_change_rate': round(job_change_rate, 2),
                'is_deleted': False
            }
        )
    
    print(f"[Trend] 총 {stacks.count()}개 스택의 트렌드 저장 완료!")