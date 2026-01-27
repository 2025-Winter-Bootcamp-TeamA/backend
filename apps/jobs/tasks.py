# apps/jobs/tasks.py

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from apps.jobs.models import TechStack, JobPosting
from apps.trends.models import TechTrend # 모델 경로 확인 필요
@shared_task
def schedule_crawling():
    """
    [Celery Beat] 주기적 크롤링 작업
    크롤링 후 관련 캐시를 무효화하여 최신 데이터 반영
    """
    print("[Celery] 정기 크롤링 작업을 시작합니다...")

    # 아까 만든 커스텀 명령어 실행 (command 이름이 'run_crawling')
    # count=50 옵션을 줘서 50개씩만 수집하도록 설정
    call_command('run_crawling', count=50)
    print("[Celery] 크롤링 작업 완료!")

    # 캐시 무효화: 크롤링으로 인해 변경된 데이터 관련 캐시 삭제
    print("[Cache] 크롤링 관련 캐시 무효화 시작...")

    # 1. 대시보드 통계 캐시 삭제 (기업 수, 채용 공고 수 변경)
    cache.delete('jobs:stats')

    # 2. 기술 스택 목록 캐시 삭제 (job_stack_count 변경 가능)
    # 모든 파라미터 조합의 캐시를 삭제하기 위해 패턴 매칭 사용
    cache_keys = cache.keys('trends:techstack:list:*')
    if cache_keys:
        cache.delete_many(cache_keys)

    print(f"[Cache] 캐시 무효화 완료: jobs:stats, {len(cache_keys) if cache_keys else 0}개의 기술 스택 목록 캐시")

@shared_task
def calculate_daily_trends():
    """
    [Celery] 일별 트렌드 집계 (채용공고 기준)
    각 날짜별로 전체 기술 스택 언급량 대비 각 기술 스택의 언급량 비율(%)을 계산하여 저장
    집계 후 관련 캐시를 무효화하여 최신 데이터 반영
    """
    now = timezone.now()
    today = now.date()

    print(f"[Trend] {today} 일자 기술 트렌드 집계 시작...")

    stacks = TechStack.objects.filter(is_deleted=False)

    # 1. 모든 기술 스택의 채용공고 카운트 계산
    tech_counts = {}
    for stack in stacks:
        current_job_count = stack.job_postings.filter(
            is_deleted=False,
            job_posting__is_deleted=False
        ).count()
        tech_counts[stack.id] = current_job_count

    # 2. 해당 날짜의 전체 기술 스택 언급량 합계 계산
    total_job_count = sum(tech_counts.values())

    # 3. 각 기술 스택별로 비율 계산 및 저장
    if total_job_count == 0:
        # 언급량이 없으면 비율 계산 불가, 모든 기술 스택에 0.0 저장
        for stack in stacks:
            TechTrend.objects.update_or_create(
                tech_stack=stack,
                reference_date=today,
                defaults={
                    'job_mention_count': 0,
                    'job_change_rate': 0.0,
                    'is_deleted': False
                }
            )
    else:
        for stack in stacks:
            current_job_count = tech_counts.get(stack.id, 0)

            # 전체 대비 비율 계산 (%)
            job_change_rate = (current_job_count / total_job_count) * 100

            # 데이터 저장
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

    # 캐시 무효화: 트렌드 집계로 인해 변경된 데이터 관련 캐시 삭제
    print("[Cache] 트렌드 집계 관련 캐시 무효화 시작...")

    # 1. 기술 스택 목록 캐시 삭제 (job_mention_count 업데이트됨)
    cache_keys = cache.keys('trends:techstack:list:*')
    if cache_keys:
        cache.delete_many(cache_keys)

    # 2. 대시보드 통계 캐시도 삭제 (job_postings_count가 변경될 수 있음)
    cache.delete('jobs:stats')

    print(f"[Cache] 캐시 무효화 완료: jobs:stats, {len(cache_keys) if cache_keys else 0}개의 기술 스택 목록 캐시")