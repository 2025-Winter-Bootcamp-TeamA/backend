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
            default=5.0,
            help='일별 변동 폭 (%). 기본값: 5 (±5%)'
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

        # 1. 시작 날짜 이전 7일간의 평균값을 기준으로 사용 (연속성 향상)
        ref_end_date = start_date - timedelta(days=1)  # 시작 날짜 하루 전
        ref_start_date = start_date - timedelta(days=7)  # 7일 전
        
        self.stdout.write(f"🔍 기준 기간({ref_start_date} ~ {ref_end_date})의 기존 데이터 조회 중...")
        
        # 각 기술 스택별 기준값 (최근 7일 평균)
        base_values = {}
        for stack in stacks:
            # 최근 7일간의 데이터 조회
            prev_trends = TechTrend.objects.filter(
                tech_stack=stack,
                reference_date__gte=ref_start_date,
                reference_date__lte=ref_end_date,
                is_deleted=False,
                article_mention_count__gt=0  # 값이 있는 데이터만
            ).values_list('article_mention_count', 'article_change_rate')
            
            if prev_trends:
                # 평균 계산
                counts = [t[0] for t in prev_trends if t[0]]
                rates = [t[1] for t in prev_trends if t[1]]
                
                avg_count = sum(counts) / len(counts) if counts else 50
                avg_rate = sum(rates) / len(rates) if rates else 1.0
                
                base_values[stack.id] = {
                    'mention_count': int(avg_count),
                    'change_rate': avg_rate
                }
            else:
                # 기존 데이터가 없으면 가장 가까운 이전 데이터 찾기
                prev_trend = TechTrend.objects.filter(
                    tech_stack=stack,
                    reference_date__lt=ref_start_date,
                    is_deleted=False,
                    article_mention_count__gt=0
                ).order_by('-reference_date').first()
                
                if prev_trend:
                    base_values[stack.id] = {
                        'mention_count': prev_trend.article_mention_count,
                        'change_rate': prev_trend.article_change_rate or 1.0
                    }
                else:
                    # 기존 데이터가 전혀 없으면 기본값 사용
                    base_values[stack.id] = {
                        'mention_count': 50,
                        'change_rate': 1.0
                    }
        
        # 기준값이 있는 기술 스택 수 출력
        stacks_with_data = sum(1 for v in base_values.values() if v['change_rate'] > 0.5)
        self.stdout.write(f"✅ 기준값 로드 완료: {stacks_with_data}개 기술 스택에 기존 데이터 있음")

        created_count = 0
        updated_count = 0

        # 이전 날짜의 비율 값을 저장 (연속성 유지)
        prev_day_rates = {stack_id: vals['change_rate'] for stack_id, vals in base_values.items()}

        with transaction.atomic():
            # 날짜별로 처리 (시작일부터 종료일까지)
            for day_offset in range(total_days):
                target_date = start_date + timedelta(days=day_offset)

                # 1. 각 기술 스택의 비율 계산 (이전 날짜 비율 기준 + 노이즈)
                # 첫 며칠은 변동을 더 작게 (부드러운 전환)
                if day_offset < 3:
                    current_noise = noise_percent * 0.3  # 첫 3일은 30% 노이즈만
                elif day_offset < 7:
                    current_noise = noise_percent * 0.6  # 다음 4일은 60% 노이즈
                else:
                    current_noise = noise_percent  # 이후는 전체 노이즈
                
                new_rates = {}
                for stack in stacks:
                    prev_rate = prev_day_rates.get(stack.id, 1.0)
                    
                    # 이전 비율 기준으로 ±current_noise 범위 내에서 변동
                    noise = random.uniform(1 - current_noise, 1 + current_noise)
                    new_rate = prev_rate * noise
                    new_rate = max(0.01, new_rate)  # 최소 0.01% 보장
                    
                    new_rates[stack.id] = new_rate

                # 2. 비율 합계를 100%로 정규화
                total_rate = sum(new_rates.values())
                
                # 3. 각 기술 스택별로 정규화된 비율 저장
                base_mention_count = 1000  # 기본 총 언급량 (비율 계산용)
                
                for stack in stacks:
                    raw_rate = new_rates.get(stack.id, 1.0)
                    
                    # 정규화된 비율 (전체 합이 100%가 되도록)
                    normalized_rate = (raw_rate / total_rate) * 100 if total_rate > 0 else 0.0
                    
                    # 언급량은 비율에 비례하여 계산
                    fake_count = int((normalized_rate / 100) * base_mention_count)
                    fake_count = max(1, fake_count)

                    # 저장 (job 필드는 유지, article 필드만 업데이트)
                    trend, created = TechTrend.objects.update_or_create(
                        tech_stack=stack,
                        reference_date=target_date,
                        defaults={
                            'article_mention_count': fake_count,
                            'article_change_rate': round(normalized_rate, 2),
                            'is_deleted': False
                        }
                    )
                    
                    # 다음 날을 위해 현재 비율 저장
                    prev_day_rates[stack.id] = normalized_rate
                    
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
