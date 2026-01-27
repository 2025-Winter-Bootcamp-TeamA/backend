"""
특정 기간 동안의 게시글 트렌드 데이터를 생성하는 명령어 (기존 데이터 기반 연속성 유지)
로직: 시작 날짜 이전의 기존 데이터를 참조하여 연속성 있는 값을 생성
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend


class Command(BaseCommand):
    help = '특정 기간 동안의 게시글 트렌드 데이터를 생성합니다 (기존 데이터 기반 연속성 유지).'

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
            '--noise-percent',
            type=float,
            default=10.0,
            help='일별 변동 폭 (%). 기본값: 10 (±10%)'
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
        
        noise_percent = options['noise_percent'] / 100.0  # 10% -> 0.1
        
        stacks = TechStack.objects.filter(is_deleted=False)
        total_days = (end_date - start_date).days + 1

        self.stdout.write(f"🚀 게시글 트렌드 데이터 생성 시작 (기존 데이터 기반)...")
        self.stdout.write(f"📅 기간: {start_date} ~ {end_date} ({total_days}일)")
        self.stdout.write(f"📊 기술 스택: {stacks.count()}개")
        self.stdout.write(f"🎲 일별 변동 폭: ±{options['noise_percent']}%")

        # 1. 시작 날짜 이전의 기존 데이터 조회 (기준값으로 사용)
        ref_date = start_date - timedelta(days=1)  # 시작 날짜 하루 전
        
        self.stdout.write(f"🔍 기준 날짜({ref_date})의 기존 데이터 조회 중...")
        
        # 각 기술 스택별 기준값 (article_mention_count, article_change_rate)
        base_values = {}
        for stack in stacks:
            # 가장 가까운 이전 데이터 찾기
            prev_trend = TechTrend.objects.filter(
                tech_stack=stack,
                reference_date__lte=ref_date,
                is_deleted=False,
                article_mention_count__gt=0  # 값이 있는 데이터만
            ).order_by('-reference_date').first()
            
            if prev_trend and prev_trend.article_mention_count > 0:
                base_values[stack.id] = {
                    'mention_count': prev_trend.article_mention_count,
                    'change_rate': prev_trend.article_change_rate or 0.0
                }
            else:
                # 기존 데이터가 없으면 기본값 사용 (다른 기술 스택과의 균형을 위해)
                base_values[stack.id] = {
                    'mention_count': 50,  # 기본 언급량
                    'change_rate': 1.0    # 기본 비율 1%
                }
        
        # 기준값이 있는 기술 스택 수 출력
        stacks_with_data = sum(1 for v in base_values.values() if v['change_rate'] > 0.5)
        self.stdout.write(f"✅ 기준값 로드 완료: {stacks_with_data}개 기술 스택에 기존 데이터 있음")

        created_count = 0
        updated_count = 0

        # 이전 날짜의 값을 저장 (연속성 유지)
        prev_day_values = {stack_id: vals.copy() for stack_id, vals in base_values.items()}

        with transaction.atomic():
            # 날짜별로 처리 (시작일부터 종료일까지)
            for day_offset in range(total_days):
                target_date = start_date + timedelta(days=day_offset)

                # 1. 각 기술 스택의 언급량 계산 (이전 날짜 기준 + 노이즈)
                tech_counts = {}
                for stack in stacks:
                    prev_vals = prev_day_values.get(stack.id, {'mention_count': 50, 'change_rate': 1.0})
                    prev_count = prev_vals['mention_count']
                    
                    # 이전 값 기준으로 ±noise_percent 범위 내에서 변동
                    noise = random.uniform(1 - noise_percent, 1 + noise_percent)
                    new_count = int(prev_count * noise)
                    new_count = max(1, new_count)  # 최소 1 보장
                    
                    tech_counts[stack.id] = new_count

                # 2. 해당 날짜의 전체 기술 스택 언급량 합계 계산
                total_article_count = sum(tech_counts.values())

                # 3. 각 기술 스택별로 비율 계산 및 저장
                for stack in stacks:
                    fake_count = tech_counts.get(stack.id, 1)
                    
                    # 전체 대비 비율 계산 (%)
                    article_change_rate = (fake_count / total_article_count) * 100 if total_article_count > 0 else 0.0

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
                    
                    # 다음 날을 위해 현재 값 저장
                    prev_day_values[stack.id] = {
                        'mention_count': fake_count,
                        'change_rate': article_change_rate
                    }
                    
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
