"""
과거 90일간의 채용공고 트렌드 데이터를 생성하는 명령어 (랜덤 노이즈 포함)
새로운 로직: 전체 기술 스택 언급량 대비 각 기술 스택의 언급량 비율(%)을 계산
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend


class Command(BaseCommand):
    help = '과거 90일간의 채용공고 트렌드 데이터를 생성합니다 (랜덤 노이즈 포함).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='생성할 기간 (일). 기본값: 90일'
        )

    def handle(self, *args, **options):
        DAYS_BACK = options.get('days', 90)
        today = timezone.now().date()
        stacks = TechStack.objects.filter(is_deleted=False)

        self.stdout.write(f"🚀 지금부터 과거 {DAYS_BACK}일 간의 트렌드 데이터를 생성합니다...")
        self.stdout.write(f"📅 기간: {today - timedelta(days=DAYS_BACK)} ~ {today}")

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            # 날짜별로 처리 (과거부터 현재까지)
            for i in range(DAYS_BACK, -1, -1):
                target_date = today - timedelta(days=i)

                # 1. 모든 기술 스택의 언급량 계산 (랜덤 노이즈 포함)
                tech_counts = {}
                for stack in stacks:
                    # A. 현재 시점 기준값
                    real_count = stack.job_postings.filter(
                        is_deleted=False,
                        job_posting__is_deleted=False
                    ).count()

                    # B. 랜덤 노이즈
                    if real_count > 0:
                        noise = random.uniform(0.7 + (0.01 * (DAYS_BACK - i)), 1.1)
                        fake_count = int(real_count * noise)
                    else:
                        fake_count = 0

                    tech_counts[stack.id] = fake_count

                # 2. 해당 날짜의 전체 기술 스택 언급량 합계 계산
                total_job_count = sum(tech_counts.values())

                # 3. 각 기술 스택별로 비율 계산 및 저장
                if total_job_count == 0:
                    # 언급량이 없으면 비율 계산 불가, 모든 기술 스택에 0.0 저장
                    for stack in stacks:
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=target_date,
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
                        fake_count = tech_counts.get(stack.id, 0)
                        
                        # 전체 대비 비율 계산 (%)
                        job_change_rate = (fake_count / total_job_count) * 100

                        # D. 저장 (article 필드는 유지)
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=target_date,
                            defaults={
                                'job_mention_count': fake_count,
                                'job_change_rate': round(job_change_rate, 2),
                                'is_deleted': False
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                # 진행 상황 출력 (매 10일마다)
                if i % 10 == 0:
                    self.stdout.write(f"  처리 중: {target_date}...")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 과거 데이터 생성 완료! 생성: {created_count:,}개, 업데이트: {updated_count:,}개"
            )
        )
