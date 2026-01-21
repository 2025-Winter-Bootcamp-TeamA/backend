from django.core.management.base import BaseCommand
from apps.trends.models import TechStack
from apps.jobs.models import JobPostingStack

class Command(BaseCommand):
    help = '기술 스택별 채용공고 연결 개수를 전체 동기화합니다.'

    def handle(self, *args, **options):
        self.stdout.write(" 채용공고 카운트 동기화 시작...")

        tech_stacks = TechStack.objects.all()
        updated_count = 0
        
        for tech in tech_stacks:
            # 1. 유효한 연결 개수 계산
            # 조건: 연결(JobPostingStack)이 삭제되지 않음 AND 원본공고(JobPosting)도 삭제되지 않음
            # related_name='job_postings' 덕분에 역참조 가능
            real_count = tech.job_postings.filter(
                is_deleted=False,
                job_posting__is_deleted=False
            ).count()

            # 2. DB값과 다르면 업데이트
            if tech.job_stack_count != real_count:
                tech.job_stack_count = real_count
                tech.save(update_fields=['job_stack_count'])
                updated_count += 1
                # (선택) 진행상황 로그 출력
                #self.stdout.write(f"  Updated {tech.name}: {real_count}개")

        self.stdout.write(self.style.SUCCESS(f" 총 {updated_count}개의 기술 스택 카운트가 최신화되었습니다."))