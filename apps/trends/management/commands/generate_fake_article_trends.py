"""
특정 기간 동안의 게시글 트렌드 데이터를 생성하는 명령어
로직: 2025년 12월 데이터를 랜덤하게 섞어서 새 기간에 적용
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend


class Command(BaseCommand):
    help = '2025년 12월 데이터를 랜덤하게 섞어서 새 기간의 게시글 트렌드 데이터를 생성합니다.'

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
            '--source-start',
            type=str,
            default='2025-12-01',
            help='소스 데이터 시작 날짜 (YYYY-MM-DD 형식). 기본값: 2025-12-01'
        )
        parser.add_argument(
            '--source-end',
            type=str,
            default='2025-12-31',
            help='소스 데이터 종료 날짜 (YYYY-MM-DD 형식). 기본값: 2025-12-31'
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
        
        # 소스 데이터 기간 파싱
        try:
            source_start = date.fromisoformat(options['source_start'])
            source_end = date.fromisoformat(options['source_end'])
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"❌ 잘못된 소스 날짜 형식: {e}"))
            return
        
        if start_date > end_date:
            self.stdout.write(self.style.ERROR("❌ 시작 날짜가 종료 날짜보다 늦습니다."))
            return
        
        stacks = list(TechStack.objects.filter(is_deleted=False))
        total_days = (end_date - start_date).days + 1

        self.stdout.write(f"🚀 게시글 트렌드 데이터 생성 시작 (12월 데이터 셔플 방식)...")
        self.stdout.write(f"📅 생성 기간: {start_date} ~ {end_date} ({total_days}일)")
        self.stdout.write(f"📅 소스 기간: {source_start} ~ {source_end}")
        self.stdout.write(f"📊 기술 스택: {len(stacks)}개")

        # 1. 각 기술 스택별로 소스 기간의 데이터 수집
        self.stdout.write(f"🔍 소스 기간({source_start} ~ {source_end})의 데이터 조회 중...")
        
        # {stack_id: [(article_mention_count, article_change_rate), ...]}
        source_data = {}
        stacks_with_data = 0
        
        for stack in stacks:
            trends = TechTrend.objects.filter(
                tech_stack=stack,
                reference_date__gte=source_start,
                reference_date__lte=source_end,
                is_deleted=False,
                article_mention_count__gt=0
            ).values_list('article_mention_count', 'article_change_rate')
            
            if trends:
                source_data[stack.id] = list(trends)
                stacks_with_data += 1
            else:
                # 소스 데이터가 없으면 기본값 리스트 생성
                source_data[stack.id] = [(50, 1.0)] * 10  # 기본값 10개
        
        self.stdout.write(f"✅ 소스 데이터 로드 완료: {stacks_with_data}개 기술 스택에 데이터 있음")

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            # 날짜별로 처리 (시작일부터 종료일까지)
            for day_offset in range(total_days):
                target_date = start_date + timedelta(days=day_offset)

                # 각 기술 스택별로 소스 데이터에서 랜덤 선택
                for stack in stacks:
                    stack_source = source_data.get(stack.id, [(50, 1.0)])
                    
                    # 랜덤하게 하나 선택
                    mention_count, change_rate = random.choice(stack_source)
                    
                    # 저장 (job 필드는 유지, article 필드만 업데이트)
                    trend, created = TechTrend.objects.update_or_create(
                        tech_stack=stack,
                        reference_date=target_date,
                        defaults={
                            'article_mention_count': mention_count,
                            'article_change_rate': round(change_rate, 2) if change_rate else 0.0,
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
