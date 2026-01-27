"""
특정 기간 동안의 게시글 트렌드 데이터를 생성하는 명령어 (랜덤 노이즈 포함)
로직: 전체 기술 스택 언급량 대비 각 기술 스택의 언급량 비율(%)을 계산
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend


class Command(BaseCommand):
    help = '특정 기간 동안의 게시글 트렌드 데이터를 생성합니다 (랜덤 노이즈 포함).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-date',
            type=str,
            default=None,
            help='시작 날짜 (YYYY-MM-DD 형식). 기본값: 2026-01-01'
        )
        parser.add_argument(
            '--to-date',
            type=str,
            default=None,
            help='종료 날짜 (YYYY-MM-DD 형식). 기본값: 오늘'
        )
        parser.add_argument(
            '--base-count',
            type=int,
            default=100,
            help='기본 언급량 (각 기술 스택별 기준값). 기본값: 100'
        )
        parser.add_argument(
            '--noise-min',
            type=float,
            default=0.5,
            help='노이즈 최소값 (배율). 기본값: 0.5'
        )
        parser.add_argument(
            '--noise-max',
            type=float,
            default=1.5,
            help='노이즈 최대값 (배율). 기본값: 1.5'
        )

    def handle(self, *args, **options):
        # 날짜 파싱
        today = timezone.now().date()
        
        if options['from_date']:
            try:
                start_date = date.fromisoformat(options['from_date'])
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ 잘못된 시작 날짜 형식: {options['from_date']}"))
                return
        else:
            start_date = date(2026, 1, 1)  # 기본값: 2026년 1월 1일
        
        if options['to_date']:
            try:
                end_date = date.fromisoformat(options['to_date'])
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ 잘못된 종료 날짜 형식: {options['to_date']}"))
                return
        else:
            end_date = today  # 기본값: 오늘
        
        if start_date > end_date:
            self.stdout.write(self.style.ERROR("❌ 시작 날짜가 종료 날짜보다 늦습니다."))
            return
        
        base_count = options['base_count']
        noise_min = options['noise_min']
        noise_max = options['noise_max']
        
        stacks = TechStack.objects.filter(is_deleted=False)
        total_days = (end_date - start_date).days + 1

        self.stdout.write(f"🚀 게시글 트렌드 데이터 생성 시작...")
        self.stdout.write(f"📅 기간: {start_date} ~ {end_date} ({total_days}일)")
        self.stdout.write(f"📊 기술 스택: {stacks.count()}개")
        self.stdout.write(f"🎲 노이즈 범위: {noise_min} ~ {noise_max}")

        created_count = 0
        updated_count = 0

        # 각 기술 스택별 기본 가중치 설정 (인기도 시뮬레이션)
        stack_weights = {}
        for stack in stacks:
            # 기본 가중치: 0.1 ~ 3.0 (랜덤)
            stack_weights[stack.id] = random.uniform(0.1, 3.0)

        with transaction.atomic():
            # 날짜별로 처리 (시작일부터 종료일까지)
            for day_offset in range(total_days):
                target_date = start_date + timedelta(days=day_offset)

                # 1. 모든 기술 스택의 언급량 계산 (랜덤 노이즈 포함)
                tech_counts = {}
                for stack in stacks:
                    # 기본값에 가중치와 노이즈 적용
                    weight = stack_weights.get(stack.id, 1.0)
                    noise = random.uniform(noise_min, noise_max)
                    
                    # 날짜에 따른 트렌드 변화 추가 (약간의 상승/하락 트렌드)
                    trend_factor = 1.0 + (day_offset / total_days) * random.uniform(-0.2, 0.3)
                    
                    fake_count = int(base_count * weight * noise * trend_factor)
                    fake_count = max(0, fake_count)  # 음수 방지
                    
                    tech_counts[stack.id] = fake_count

                # 2. 해당 날짜의 전체 기술 스택 언급량 합계 계산
                total_article_count = sum(tech_counts.values())

                # 3. 각 기술 스택별로 비율 계산 및 저장
                if total_article_count == 0:
                    # 언급량이 없으면 비율 계산 불가, 모든 기술 스택에 0.0 저장
                    for stack in stacks:
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=target_date,
                            defaults={
                                'article_mention_count': 0,
                                'article_change_rate': 0.0,
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
                        article_change_rate = (fake_count / total_article_count) * 100

                        # 저장 (job 필드는 유지, article 필드만 업데이트)
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=stack,
                            reference_date=target_date,
                            defaults={
                                'article_mention_count': fake_count,
                                'article_change_rate': round(article_change_rate, 2),
                                'is_deleted': False
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                # 진행 상황 출력 (매 7일마다)
                if day_offset % 7 == 0:
                    self.stdout.write(f"  처리 중: {target_date}...")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 게시글 트렌드 데이터 생성 완료! 생성: {created_count:,}개, 업데이트: {updated_count:,}개"
            )
        )
