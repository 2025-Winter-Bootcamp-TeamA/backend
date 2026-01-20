import csv
import re
from collections import defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse

from django.core.management.base import BaseCommand

# 토큰 추출용
TOKEN_RE = re.compile(r"[a-z0-9\+\#\.\-]+")


# 기술명 표준화 (공백 정리, 소문자화)
def normalize_spaces(s: str) -> str:
    return " ".join((s or "").split())

def normalize_tech_name(name: str) -> str:
    return normalize_spaces(name).lower()


# xml 태그 표준화
def normalize_tags(tags: str) -> str:
    t = tags or ""
    if "|" in t:
        # |tag|tag| 형태
        return normalize_spaces(t.replace("|", " "))
    # <tag><tag> 형태
    return normalize_spaces(t.replace("><", "> <").replace("<", " ").replace(">", " "))


# xml 게시글 표준화
def normalize_post_text(title: str, body: str, tags: str) -> str:
    tags_clean = normalize_tags(tags)
    text = f"{title or ''} {body or ''} {tags_clean}"
    return normalize_spaces(text).lower()


# teck_stacks_source.csv 로드
def load_techs_from_csv(csv_path: Path) -> list[str]:
    """Name 컬럼만 읽어서 기술 목록 생성"""
    techs: list[str] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        if "Name" not in fields:
            raise ValueError(f"CSV must contain a 'Name' column. Found: {fields}")
        
        for row in reader:
            tech = normalize_tech_name(row.get("Name") or "")
            if tech:
                techs.append(tech)

    # 중복 제거
    seen = set()
    uniq = []
    for t in techs:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq


# xml 스트리밍 파싱
def iter_posts(posts_xml_path: Path):
    context = iterparse(posts_xml_path, events=("end",))
    for _, elem in context:
        if elem.tag != "row":
            continue

        a = elem.attrib
        title = a.get("Title") or ""
        body = a.get("Body") or ""
        tags = a.get("Tags") or ""
        view_count_raw = a.get("ViewCount") or "0"

        try:
            view_count = int(view_count_raw)
        except ValueError:
            view_count = 0

        # 대용량 메모리 방지
        elem.clear()

        yield title, body, tags, view_count


# "react native" 처럼 여러 단어 기술이 문장에 붙어서 나왔는지 확인
def tokens_match(tech_tokens: list[str], post_tokens: list[str]) -> bool:
    """tech 토큰 시퀀스가 post_tokens에 '연속으로' 등장하는지 확인"""
    if not tech_tokens:
        return False

    L = len(tech_tokens)
    if L > len(post_tokens):
        return False

    for i in range(len(post_tokens) - L + 1):
        if post_tokens[i : i + L] == tech_tokens:
            return True
    return False

# 성능용 후보 축소 인덱스
# - single_index: 단일 토큰 기술(예: redis, kafka) -> 토큰으로 매칭 후보 찾기
# - multi_index: 다중 토큰 기술(예: github actions) -> 첫 토큰으로 후보 찾고 최종은 'tech in text'
def build_tech_index(techs: list[str]):
    single_index = defaultdict(list)
    multi_index = defaultdict(list)
    tech_tokens_map = {}

    for tech in techs:
        tokens = TOKEN_RE.findall(tech)
        if not tokens:
            continue

        tech_tokens_map[tech] = tokens

        if len(tokens) == 1:
            single_index[tokens[0]].append(tech)
        else:
            multi_index[tokens[0]].append(tech)

    return single_index, multi_index, tech_tokens_map


class Command(BaseCommand):
    help = (
        "Analyze StackOverflow Posts.xml by simple string matching against our tech stack CSV (Name column). "
        "Counts mentions and aggregates view counts, then sorts by total views."
    )

    def add_arguments(self, parser):
        parser.add_argument("--posts", required=True, help="Path to Posts.xml (or sample xml)")
        parser.add_argument("--stacks", required=True, help="Path to tech_stacks_source.csv (Name/Image/Link)")
        parser.add_argument("--out", required=True, help="Output CSV path")
        parser.add_argument("--limit", type=int, default=0, help="Optional: limit number of rows to scan (0=no limit)")
        parser.add_argument("--progress", type=int, default=10000, help="Print progress every N rows")

    def handle(self, *args, **options):
        posts_path = Path(options["posts"]).expanduser()
        stacks_path = Path(options["stacks"]).expanduser()
        out_path = Path(options["out"]).expanduser()
        limit = int(options["limit"])
        progress = int(options["progress"])

        if not posts_path.exists():
            self.stderr.write(self.style.ERROR(f"Posts file not found: {posts_path}"))
            return
        if not stacks_path.exists():
            self.stderr.write(self.style.ERROR(f"Stacks CSV not found: {stacks_path}"))
            return

        try:
            techs = load_techs_from_csv(stacks_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to load stacks CSV: {e}"))
            return

        if not techs:
            self.stderr.write(self.style.ERROR("No techs loaded from CSV (Name column empty?)."))
            return

        single_index, multi_index, tech_tokens_map = build_tech_index(techs)

        # 결과 집계용
        mention_count = defaultdict(int)  # tech -> 언급된 게시글 수
        total_views = defaultdict(int)    # tech -> 조회수 누적 합

        scanned = 0

        for title, body, tags, view_count in iter_posts(posts_path):
            scanned += 1
            if limit and scanned > limit:
                break

            text = normalize_post_text(title, body, tags)
            post_tokens = TOKEN_RE.findall(text)

            # 한 게시글에서 같은 tech를 여러 번 카운트하지 않도록 방지
            seen_in_this_post = set()

            # 1) 단일 토큰 기술: 토큰 등장으로 후보를 바로 매칭
            for tok in post_tokens:
                for tech in single_index.get(tok, []):
                    if tech in seen_in_this_post:
                        continue
                    mention_count[tech] += 1
                    total_views[tech] += view_count
                    seen_in_this_post.add(tech)

            # 2) 다중 토큰 기술: 첫 토큰이 등장했을 때만 후보 검사, 최종은 문자열 포함 비교
            for tok in set(post_tokens):
                for tech in multi_index.get(tok, []):
                    if tech in seen_in_this_post:
                        continue
                    tech_tokens = tech_tokens_map[tech]
                    if tokens_match(tech_tokens, post_tokens):
                        mention_count[tech] += 1
                        total_views[tech] += view_count
                        seen_in_this_post.add(tech)

            if progress and scanned % progress == 0:
                self.stdout.write(f"scanned={scanned:,}")

        # 조회수(total_views) 기준 정렬해서 CSV 출력
        rows = []
        for tech in techs:
            m = mention_count[tech]
            v = total_views[tech]
            rows.append(
                {
                    "tech": tech,
                    "mentions": m,
                    "total_views": v,
                    "avg_views_per_mention": (v / m) if m else 0,
                }
            )

        rows.sort(key=lambda r: r["total_views"], reverse=True)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["tech", "mentions", "total_views", "avg_views_per_mention"],
            )
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Done. scanned={scanned:,} output={out_path}"))
