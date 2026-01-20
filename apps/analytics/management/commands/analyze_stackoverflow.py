import csv
import re
import heapq
from collections import defaultdict
from pathlib import Path
from xml.etree.ElementTree import iterparse

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.trends.models import TechStack, Article, ArticleStack

# 토큰 추출용
TOKEN_RE = re.compile(r"[a-z0-9\+\#\.\-]+")

# 노이즈로 튀는 기술명 필터링
NOISE_TECHS = {
    "d", "q",
    "make", "simple", "mean", "parse", "render", "echo", "stream", "buffer", "heap",
    "box", "hub", "dash", "flux", "salt", "ent", "tower", "buddy",
    "play", "linear", "segment", "prism", "foundation", "slick", "realm", "crystal",
}

# 필터링 하면 안되는 기술명
KNOWN_SHORT_TECHS = {"go", "r", "d3", "qt"}

def is_noise_tech(normalized_tech: str) -> bool:

    if normalized_tech in KNOWN_SHORT_TECHS:
        return False
    
    if not normalized_tech:
        return True

    if normalized_tech in NOISE_TECHS:
        return True

    toks = TOKEN_RE.findall(normalized_tech)
    if not toks:
        return True

    # 단일 토큰인데 "알파벳만" && "길이 <= 2" 이면 노이즈로 처리
    if len(toks) == 1:
        t = toks[0]
        if t.isalpha() and len(t) <= 2:
            return True

    return False


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
        post_id = a.get("Id") or ""
        post_type = a.get("PostTypeId") or "" # 1=Question, 2=Answer
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

        yield post_id, post_type, title, body, tags, view_count


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

        parser.add_argument(  # 전체 기술 topN 저장 토글
            "--with-top-posts",
            action="store_true",
            help="If set, store tech-wise top posts into out.csv as top_posts column.",
        )
        
        # 특정 기술의 top N posts 추출 (예: git)
        parser.add_argument(
            "--detail-tech",
            default="",
            help="Extract top posts for this tech (normalized, e.g. 'git'). Leave empty to skip.",
        )
        parser.add_argument(
            "--topn",
            type=int,
            default=10,
            help="How many top posts to keep for --detail-tech (default 10)",
        )

        # detail-tech 결과를 별도 파일로 저장할지/경로 (원하면 지정)
        parser.add_argument(  
            "--detail-out",   
            default="",        
            help="Optional: output CSV path for --detail-tech results. "
                 "If empty, auto-generate next to --out (e.g. git_top_posts_10.csv).",
        )  

        # DB 에 게시글, 게시글-기술스택 저장 옵션
        parser.add_argument(
            "--save-db",
            action="store_true",
            help="If set, save Article and ArticleStack into DB.",
        )

        # DB 적재 배치 크기(ArticleStack bulk)
        parser.add_argument(
            "--db-batch",
            type=int,
            default=2000,
            help="Bulk insert batch size for ArticleStack when --save-db is set.",
        )


    def handle(self, *args, **options):
        posts_path = Path(options["posts"]).expanduser()
        stacks_path = Path(options["stacks"]).expanduser()
        out_path = Path(options["out"]).expanduser()
        limit = int(options["limit"])
        progress = int(options["progress"])

        with_top_posts = bool(options["with_top_posts"])
        topn = int(options["topn"])

        detail_tech = normalize_tech_name(options.get("detail_tech") or "")
        detail_out_opt = (options.get("detail_out") or "").strip()           

        save_db = bool(options.get("save_db")) 
        db_batch = int(options.get("db_batch"))

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
        
        techs = [t for t in techs if not is_noise_tech(t)]

        if not techs:
            self.stderr.write(self.style.ERROR("No techs loaded from CSV (Name column empty?)."))
            return

        # DB TechStack를 '소문자 normalize'해서 매핑 생성 (대소문자 그대로인 DB와 매칭하기 위함)
        db_tech_map = {}
        if save_db:
            qs = TechStack.objects.filter(is_deleted=False).only("id", "name")
            db_tech_map = {normalize_tech_name(t.name): t for t in qs}

            if not db_tech_map:
                self.stderr.write(self.style.ERROR("TechStack table is empty. Seed TechStack first."))
                return

            # CSV 기술 중 DB에 실제 존재하는 기술만 분석 대상으로 유지
            techs = [t for t in techs if t in db_tech_map]
            if not techs:
                self.stderr.write(self.style.ERROR("No CSV techs matched TechStack(name) in DB after normalization."))
                return

        tech_set = set(techs) 

        if detail_tech and detail_tech not in tech_set: 
            self.stderr.write(self.style.ERROR(f"--detail-tech '{detail_tech}' not found in stacks CSV"))  # ✅
            return 
        
        single_index, multi_index, tech_tokens_map = build_tech_index(techs)

        # 결과 집계용
        mention_count = defaultdict(int)  # tech -> 언급된 게시글 수
        total_views = defaultdict(int)    # tech -> 조회수 누적 합

        top_posts_by_tech = defaultdict(list)
        detail_heap = []

        scanned = 0

        # ArticleStack bulk insert 버퍼
        rel_buffer = [] 

        for post_id, post_type, title, body, tags, view_count in iter_posts(posts_path):
            if post_type != "1":
                continue

            scanned += 1
            if limit and scanned > limit:
                break

            text = normalize_post_text(title, body, tags)
            post_tokens = TOKEN_RE.findall(text)
            post_tok_set = set(post_tokens)

            seen_in_this_post = set()

            # 1) 단일 토큰 기술
            for tok in post_tok_set:
                for tech in single_index.get(tok, []):
                    if tech in seen_in_this_post:
                        continue
                    mention_count[tech] += 1
                    total_views[tech] += view_count
                    seen_in_this_post.add(tech)

            # 2) 다중 토큰 기술
            for tok in post_tok_set:
                for tech in multi_index.get(tok, []):
                    if tech in seen_in_this_post:
                        continue
                    tech_tokens = tech_tokens_map[tech]
                    if tokens_match(tech_tokens, post_tokens):
                        mention_count[tech] += 1
                        total_views[tech] += view_count
                        seen_in_this_post.add(tech)

            # 3) 특정 기술(detail_tech)의 topN 유지 (조회수 기준)
            if detail_tech and detail_tech in seen_in_this_post: 
                heapq.heappush(detail_heap, (view_count, post_id, title)) 
                if len(detail_heap) > topn:  
                    heapq.heappop(detail_heap)

            # 4) tech별 topN 유지
            if with_top_posts and seen_in_this_post:
                for tech in seen_in_this_post:
                    h = top_posts_by_tech[tech]
                    heapq.heappush(h, (view_count, post_id, title))
                    if len(h) > topn:
                        heapq.heappop(h)

            # 5) DB 저장: Article / ArticleStack 적재
            if save_db and seen_in_this_post:
                url = f"https://stackoverflow.com/questions/{post_id}"

                article, created = Article.objects.get_or_create( 
                    url=url,
                    defaults={
                        "source": "stackoverflow",
                        "stack_count": 0,
                        "view_count": view_count
                    },
                )

                # ✅ 이미 존재하는 글이면 view_count 최신값으로 갱신
                if not created and article.view_count != view_count:
                    article.view_count = view_count
                    article.save(update_fields=["view_count", "updated_at"])  

                # 관계 버퍼에 쌓고 배치로 bulk_create
                for tech in seen_in_this_post:
                    ts = db_tech_map.get(tech)
                    if not ts:
                        continue
                    rel_buffer.append(
                        ArticleStack(
                            article=article,
                            tech_stack=ts,
                            count=1,
                        )
                    )

                # 일정량 쌓이면 bulk insert
                if len(rel_buffer) >= db_batch:
                    with transaction.atomic():  
                        ArticleStack.objects.bulk_create(rel_buffer, batch_size=db_batch,  ignore_conflicts=True)  
                    rel_buffer.clear()  

            if progress and scanned % progress == 0:
                self.stdout.write(f"scanned={scanned:,}")

        # 남은 관계 버퍼 flush
        if save_db and rel_buffer: 
            with transaction.atomic(): 
                ArticleStack.objects.bulk_create(rel_buffer, batch_size=db_batch, ignore_conflicts=True) 
            rel_buffer.clear() 

        # 조회수(total_views) 기준 정렬해서 CSV 출력
        rows = []
        for tech in techs:
            m = mention_count[tech]
            v = total_views[tech]
            row = {
                "tech": tech,
                "mentions": m,
                "total_views": v,
                "avg_views_per_mention": (v / m) if m else 0,
            }

            if with_top_posts:
                heap = top_posts_by_tech.get(tech, [])
                top_posts = sorted(heap, reverse=True)
                parts = []
                for vc, pid, t in top_posts:
                    url = f"https://stackoverflow.com/questions/{pid}"
                    t_clean = normalize_spaces(t).replace("\n", " ").replace("\r", " ")
                    parts.append(f"{vc}|{url}|{t_clean}")
                row["top_posts"] = " ; ".join(parts)

            rows.append(row)

        rows.sort(key=lambda r: r["total_views"], reverse=True)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["tech", "mentions", "total_views", "avg_views_per_mention"]
        if with_top_posts:
            fieldnames.append("top_posts")

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # detail-tech 결과를 별도 CSV로 저장 (조회수 내림차순)
        if detail_tech: 
            if detail_out_opt:  
                detail_out_path = Path(detail_out_opt).expanduser()  
            else:
                detail_out_path = out_path.with_name(f"{detail_tech}_top_posts_{topn}.csv")  

            detail_out_path.parent.mkdir(parents=True, exist_ok=True)  

            detail_rows = []  
            for vc, pid, t in sorted(detail_heap, reverse=True):  
                detail_rows.append(  
                    {
                        "tech": detail_tech,
                        "post_id": pid,
                        "url": f"https://stackoverflow.com/questions/{pid}",
                        "view_count": vc,
                        "title": normalize_spaces(t).replace("\n", " ").replace("\r", " "),
                    }
                )

            with detail_out_path.open("w", newline="", encoding="utf-8") as df:  
                dw = csv.DictWriter(df, fieldnames=["tech", "post_id", "url", "view_count", "title"])  
                dw.writeheader()  
                dw.writerows(detail_rows)  

            self.stdout.write(self.style.SUCCESS(f"Detail saved: {detail_out_path}"))

        self.stdout.write(self.style.SUCCESS(f"Done. scanned={scanned:,} output={out_path}"))
