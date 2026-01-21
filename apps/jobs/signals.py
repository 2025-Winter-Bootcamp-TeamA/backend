from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import JobPostingStack

@receiver([post_save, post_delete], sender=JobPostingStack)
def update_job_stack_count(sender, instance, **kwargs):
    """
    JobPostingStack(연결 테이블)이 생성/수정/삭제될 때마다
    해당 기술 스택의 총 채용공고 언급량을 다시 계산하여 갱신합니다.
    """
    try:
        tech_stack = instance.tech_stack
        
        # 현재 유효한 공고 개수 다시 세기 (동기화 스크립트와 동일한 로직)
        active_count = tech_stack.job_postings.filter(
            is_deleted=False,
            job_posting__is_deleted=False
        ).count()
        #디버그 코드
        #print(f" [Signal 작동] {tech_stack.name}의 카운트를 {active_count}개로 갱신 시도 중...")
        # 개수 업데이트
        # 불필요한 DB 쓰기를 줄이기 위해 값이 다를 때만 저장
        if tech_stack.job_stack_count != active_count:
            tech_stack.job_stack_count = active_count
            tech_stack.save(update_fields=['job_stack_count'])
            
    except Exception as e:
        print(f"카운트 업데이트 중 에러 발생: {e}")