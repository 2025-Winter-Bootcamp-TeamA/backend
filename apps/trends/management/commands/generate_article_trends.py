"""
Posts.xml에서 날짜별 기술 스택 언급량 집계 및 tech_trend 테이블의 article_mention_count, article_change_rate 업데이트
"""
import re
from collections import defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse
from datetime import datetime, date, timedelta, timezone

from django.core.management.base import BaseCommand
from django.utils import timezone as django_timezone
from django.db import transaction

from apps.trends.models import TechStack, TechTrend


# analyze_stackoverflow.py와 동일한 유틸리티 함수들
TOKEN_RE = re.compile(r"[a-z0-9\+\#\.\-]+")

NOISE_TECHS = {
    "d", "q",
    "make", "simple", "mean", "parse", "render", "echo", "stream", "buffer", "heap",
    "box", "hub", "dash", "flux", "salt", "ent", "tower", "buddy",
    "play", "linear", "segment", "prism", "foundation", "slick", "realm", "crystal",
}
KNOWN_SHORT_TECHS = {"go", "r", "d3", "qt"}


def is_noise_tech(normalized_tech: str) -> bool:
    if normalized_tech in KNOWN_SHORT_TECHS:
        return False
    if not normalized_tech or normalized_tech in NOISE_TECHS:
        return True
    toks = TOKEN_RE.findall(normalized_tech)
    if not toks:
        return True
    if len(toks) == 1:
        t = toks[0]
        if t.isalpha() and len(t) <= 2:
            return True
    return False


def normalize_spaces(s: str) -> str:
    return " ".join((s or "").split())


def normalize_tech_name(name: str) -> str:
    return normalize_spaces(name).lower()


def normalize_tags(tags: str) -> str:
    t = tags or ""
    if "|" in t:
        return normalize_spaces(t.replace("|", " "))
    return normalize_spaces(t.replace("><", "> <").replace("<", " ").replace(">", " "))


def normalize_post_text(title: str, body: str, tags: str) -> str:
    tags_clean = normalize_tags(tags)
    text = f"{title or ''} {body or ''} {tags_clean}"
    return normalize_spaces(text).lower()


def parse_creation_dt(s: str) -> datetime | None:
    """CreationDate -> datetime(UTC) (analyze_stackoverflow.py와 동일)"""
    if not s:
        return None
    try:
        # Z가 있으면 +00:00로 바꿔서 파싱
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        # tz 없는 값이면 UTC로 강제
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def iter_posts_with_date(posts_xml_path: Path):
    """Posts.xml을 파싱하여 (post_id, post_type, title, body, tags, created_at) 반환"""
    context = iterparse(posts_xml_path, events=("end",))
    try:
        for _, elem in context:
            if elem.tag != "row":
                continue

            a = elem.attrib
            post_id = a.get("Id") or ""
            post_type = a.get("PostTypeId") or ""
            title = a.get("Title") or ""
            body = a.get("Body") or ""
            tags = a.get("Tags") or ""
            created_raw = a.get("CreationDate") or ""

            created_at = parse_creation_dt(created_raw)

            elem.clear()
            yield post_id, post_type, title, body, tags, created_at
    except Exception as e:
        import sys
        print(f"Warning: XML parsing error: {e}", file=sys.stderr)


def tokens_match(tech_tokens: list[str], post_tokens: list[str]) -> bool:
    """tech 토큰 시퀀스가 post_tokens에 연속으로 등장하는지 확인"""
    if not tech_tokens:
        return False
    L = len(tech_tokens)
    if L > len(post_tokens):
        return False
    for i in range(len(post_tokens) - L + 1):
        if post_tokens[i:i + L] == tech_tokens:
            return True
    return False


def build_tech_index(tech_stacks):
    """TechStack 쿼리셋을 인덱스로 변환"""
    single_index = defaultdict(list)
    multi_index = defaultdict(list)
    tech_tokens_map = {}
    tech_id_map = {}  # normalized_tech -> tech_stack_id

    for tech_stack in tech_stacks:
        tech_name = normalize_tech_name(tech_stack.name)
        if is_noise_tech(tech_name):
            continue

        tokens = TOKEN_RE.findall(tech_name)
        if not tokens:
            continue

        tech_tokens_map[tech_name] = tokens
        tech_id_map[tech_name] = tech_stack.id

        if len(tokens) == 1:
            single_index[tokens[0]].append(tech_name)
        else:
            multi_index[tokens[0]].append(tech_name)

    return single_index, multi_index, tech_tokens_map, tech_id_map


class Command(BaseCommand):
    help = 'Posts.xml에서 날짜별 기술 스택 언급량을 집계하여 tech_trend 테이블의 article_mention_count, article_change_rate를 업데이트합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--posts',
            type=str,
            required=True,
            help='Posts.xml 파일 경로'
        )
        parser.add_argument(
            '--progress',
            type=int,
            default=10000,
            help='진행 상황 출력 간격 (기본값: 10000개)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='현재 날짜 기준 최근 N일 데이터만 추출 (기본값: None, 전체 기간 처리)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='기존 article_mention_count, article_change_rate 데이터를 모두 삭제 (0으로 초기화)'
        )

    def handle(self, *args, **options):
        posts_path = Path(options['posts']).expanduser()
        progress_interval = options['progress']
        days = options['days']
        clear_existing = options['clear_existing']

        if not posts_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ 파일을 찾을 수 없습니다: {posts_path}"))
            return

        # 기존 데이터 삭제
        if clear_existing:
            self.stdout.write("🗑️  기존 article_mention_count, article_change_rate 데이터 삭제 중...")
            deleted_count = TechTrend.objects.filter(
                article_mention_count__gt=0
            ).update(
                article_mention_count=0,
                article_change_rate=0.0
            )
            self.stdout.write(f"✅ {deleted_count:,}개 레코드의 게시글 데이터 삭제 완료")

        # 날짜 범위 계산 (days가 지정되지 않으면 전체 기간 처리)
        start_date = None
        end_date = None
        if days:
            end_date = django_timezone.now().date()
            start_date = end_date - timedelta(days=days - 1)
            self.stdout.write(f"📊 Posts.xml에서 날짜별 기술 스택 언급량 집계 시작...")
            self.stdout.write(f"📁 Posts.xml: {posts_path}")
            self.stdout.write(f"📅 기간: {start_date} ~ {end_date} (최근 {days}일)")
        else:
            self.stdout.write(f"📊 Posts.xml에서 날짜별 기술 스택 언급량 집계 시작...")
            self.stdout.write(f"📁 Posts.xml: {posts_path}")
            self.stdout.write(f"📅 기간: 전체 (날짜 필터링 없음)")

        # 1. TechStack 로드 및 인덱스 생성
        self.stdout.write("🔍 기술 스택 인덱스 생성 중...")
        tech_stacks = TechStack.objects.filter(is_deleted=False)
        single_index, multi_index, tech_tokens_map, tech_id_map = build_tech_index(tech_stacks)
        self.stdout.write(f"✅ {len(tech_id_map)}개 기술 스택 로드 완료")

        # 2. 날짜별, 기술 스택별 언급량 집계
        trends_data = defaultdict(lambda: defaultdict(int))  # {date: {tech_id: count}}
        scanned = 0
        processed = 0

        self.stdout.write("📖 Posts.xml 파싱 중...")

        for post_id, post_type, title, body, tags, created_at in iter_posts_with_date(posts_path):
            scanned += 1

            if scanned % progress_interval == 0:
                self.stdout.write(f"  스캔: {scanned:,}개, 처리: {processed:,}개...")

            # Question만 처리 (PostTypeId == "1")
            if post_type != "1":
                continue

            # 날짜 필터링 (생성일이 없으면 스킵)
            if not created_at:
                continue

            created_date = created_at.date()
            
            # 날짜 필터링 (days 옵션이 지정된 경우만)
            if days and (created_date < start_date or created_date > end_date):
                continue

            processed += 1

            # 게시글 텍스트 정규화 및 토큰화
            text = normalize_post_text(title, body, tags)
            post_tokens = TOKEN_RE.findall(text)
            post_tok_set = set(post_tokens)

            seen_in_this_post = set()

            # 단일 토큰 기술 매칭
            for tok in post_tok_set:
                for tech_name in single_index.get(tok, []):
                    if tech_name in seen_in_this_post:
                        continue
                    tech_id = tech_id_map[tech_name]
                    trends_data[created_date][tech_id] += 1
                    seen_in_this_post.add(tech_name)

            # 다중 토큰 기술 매칭
            for tok in post_tok_set:
                for tech_name in multi_index.get(tok, []):
                    if tech_name in seen_in_this_post:
                        continue
                    tech_tokens = tech_tokens_map[tech_name]
                    if tokens_match(tech_tokens, post_tokens):
                        tech_id = tech_id_map[tech_name]
                        trends_data[created_date][tech_id] += 1
                        seen_in_this_post.add(tech_name)

        self.stdout.write(f"✅ 총 {scanned:,}개 게시글 스캔, {processed:,}개 Question 처리 완료")
        
        # 집계된 데이터 확인
        total_mentions = sum(sum(counts.values()) for counts in trends_data.values())
        self.stdout.write(f"📊 집계 완료: {len(trends_data)}일, 총 {total_mentions:,}개 언급")
        if trends_data:
            sample_date = sorted(trends_data.keys())[0]
            sample_count = len(trends_data[sample_date])
            self.stdout.write(f"   예시: {sample_date} - {sample_count}개 기술 스택")

        # 3. tech_trend 테이블에 저장/업데이트
        # 각 날짜별로 전체 기술 스택 언급량 대비 각 기술 스택의 언급량 비율(%)을 계산하여 저장
        self.stdout.write("💾 tech_trend 테이블 저장 중...")
        created_count = 0
        updated_count = 0

        sorted_dates = sorted(trends_data.keys())

        with transaction.atomic():
            for ref_date in sorted_dates:
                tech_counts = trends_data[ref_date]

                # 해당 날짜의 전체 기술 스택 언급량 합계 계산
                total_mentions = sum(tech_counts.values())
                
                if total_mentions == 0:
                    # 언급량이 없으면 비율 계산 불가, 모든 기술 스택에 0.0 저장
                    for tech_id in tech_counts.keys():
                        try:
                            tech_stack = TechStack.objects.get(id=tech_id, is_deleted=False)
                        except TechStack.DoesNotExist:
                            continue
                        
                        trend, created = TechTrend.objects.update_or_create(
                            tech_stack=tech_stack,
                            reference_date=ref_date,
                            defaults={
                                'article_mention_count': 0,
                                'article_change_rate': 0.0,
                                'is_deleted': False,
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    continue

                # 각 기술 스택별로 비율 계산 및 저장
                for tech_id, mention_count in tech_counts.items():
                    try:
                        tech_stack = TechStack.objects.get(id=tech_id, is_deleted=False)
                    except TechStack.DoesNotExist:
                        continue

                    # 전체 대비 비율 계산 (%)
                    article_change_rate = (mention_count / total_mentions) * 100

                    # TechTrend 생성 또는 업데이트 (article 필드만 업데이트, job 필드는 유지)
                    trend, created = TechTrend.objects.update_or_create(
                        tech_stack=tech_stack,
                        reference_date=ref_date,
                        defaults={
                            'article_mention_count': mention_count,
                            'article_change_rate': round(article_change_rate, 2),
                            'is_deleted': False,
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 완료! 생성: {created_count:,}개, 업데이트: {updated_count:,}개"
            )
        )
