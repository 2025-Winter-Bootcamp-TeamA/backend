"""
채용공고 트렌드 데이터를 새로운 로직(전체 대비 비율)으로 다시 계산하는 명령어
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend
from apps.jobs.models import JobPosting


class Command(BaseCommand):
    help = '채용공고 트렌드 데이터를 새로운 로직(전체 대비 비율)으로 다시 계산합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-date',
            type=str,
            default=None,
            help='시작 날짜 (YYYY-MM-DD 형식). 기본값: None (전체 기간)'
        )
        parser.add_argument(
            '--to-date',
            type=str,
            default=None,
            help='종료 날짜 (YYYY-MM-DD 형식). 기본값: 오늘 날짜'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='현재 날짜 기준 최근 N일 데이터만 재계산 (기본값: None)'
        )

    def handle(self, *args, **options):
        from_date_str = options.get('from_date')
        to_date_str = options.get('to_date')
        days = options.get('days')

        # 날짜 범위 계산
        if days:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days - 1)
            self.stdout.write(f"📊 최근 {days}일 데이터 재계산: {start_date} ~ {end_date}")
        else:
            if from_date_str:
                try:
                    start_date = date.fromisoformat(from_date_str)
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"❌ 잘못된 날짜 형식: {from_date_str}. YYYY-MM-DD 형식을 사용하세요."))
                    return
            else:
                start_date = None

            if to_date_str:
                try:
                    end_date = date.fromisoformat(to_date_str)
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"❌ 잘못된 날짜 형식: {to_date_str}. YYYY-MM-DD 형식을 사용하세요."))
                    return
            else:
                end_date = timezone.now().date()

            if start_date and start_date > end_date:
                self.stdout.write(self.style.ERROR(f"❌ 시작 날짜가 종료 날짜보다 늦습니다."))
                return

            self.stdout.write(f"📊 채용공고 트렌드 재계산 시작...")
            if start_date:
                self.stdout.write(f"📅 기간: {start_date} ~ {end_date}")
            else:
                self.stdout.write(f"📅 기간: ~ {end_date} (전체)")

        # TechStack 로드
        stacks = TechStack.objects.filter(is_deleted=False)
        self.stdout.write(f"✅ {stacks.count()}개 기술 스택 로드 완료")

        # 날짜별로 처리
        if start_date:
            current_date = start_date
        else:
            # start_date가 없으면 가장 오래된 JobPosting의 날짜부터 시작
            oldest_posting = JobPosting.objects.filter(is_deleted=False).order_by('created_at').first()
            if oldest_posting:
                current_date = oldest_posting.created_at.date()
            else:
                self.stdout.write(self.style.WARNING("⚠️  채용공고 데이터가 없습니다."))
                return

        updated_count = 0
        created_count = 0

        with transaction.atomic():
            while current_date <= end_date:
                # 해당 날짜까지 생성된 채용공고만 고려
                # (즉, created_at <= current_date인 채용공고)
                job_postings_by_date = JobPosting.objects.filter(
                    is_deleted=False,
                    created_at__date__lte=current_date
                )

                # 각 기술 스택별 채용공고 카운트 계산
                tech_counts = {}
                for stack in stacks:
                    count = stack.job_postings.filter(
                        is_deleted=False,
                        job_posting__is_deleted=False,
                        job_posting__created_at__date__lte=current_date
                    ).count()
                    tech_counts[stack.id] = count

                # 전체 언급량 합계
                total_job_count = sum(tech_counts.values())

                # 각 기술 스택별로 비율 계산 및 저장
                if total_job_count == 0:
                    # 언급량이 없으면 비율 계산 불가, 모든 기술 스택에 0.0 저장
                    for stack in stacks:
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=current_date,
                            defaults={
                                'job_mention_count': 0,
                                'job_change_rate': 0.0,
                                'is_deleted': False
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                else:
                    for stack in stacks:
                        current_job_count = tech_counts.get(stack.id, 0)
                        
                        # 전체 대비 비율 계산 (%)
                        job_change_rate = (current_job_count / total_job_count) * 100
                        
                        # 데이터 저장 (article 필드는 유지)
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=current_date,
                            defaults={
                                'job_mention_count': current_job_count,
                                'job_change_rate': round(job_change_rate, 2),
                                'is_deleted': False
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                # 다음 날짜로 이동
                current_date += timedelta(days=1)

                # 진행 상황 출력 (매 30일마다)
                if (current_date - start_date if start_date else timedelta(days=0)).days % 30 == 0:
                    self.stdout.write(f"  처리 중: {current_date - timedelta(days=1)}...")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 완료! 생성: {created_count:,}개, 업데이트: {updated_count:,}개"
            )
        )
