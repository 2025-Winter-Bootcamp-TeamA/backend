import requests
import time
import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.jobs.models import Corp, JobPosting, JobPostingStack
from apps.trends.models import TechStack
# [주석 처리] skill_tags 방식 사용하지 않음
# from fuzzywuzzy import process  # 문자열 유사도 매칭을 위해 필수
import requests
import os

# 토큰 추출용 정규식 (기술명에서 토큰 추출)
TOKEN_RE = re.compile(r"[a-z0-9\+\#\.\-]+")

# 노이즈 기술명 필터링 (너무 일반적인 단어)
NOISE_TECHS = {
    "d", "q", "make", "simple", "mean", "parse", "render", "echo", "stream", "buffer",
    "box", "hub", "dash", "flux", "salt", "ent", "tower", "buddy", "play", "linear",
    "segment", "prism", "foundation", "slick", "realm", "crystal", "heap",
}

# 필터링하면 안 되는 짧은 기술명
KNOWN_SHORT_TECHS = {"go", "r", "d3", "qt", "c", "c#", "c++"}


def normalize_text(text: str) -> str:
    """텍스트 정규화 (소문자, 공백 정리)"""
    return " ".join((text or "").lower().split())


def is_noise_tech(tech: str) -> bool:
    """노이즈 기술명인지 확인"""
    if tech in KNOWN_SHORT_TECHS:
        return False
    if not tech or tech in NOISE_TECHS:
        return True
    tokens = TOKEN_RE.findall(tech)
    if not tokens:
        return True
    # 단일 토큰이면서 알파벳만 있고 길이가 2 이하면 노이즈
    if len(tokens) == 1:
        t = tokens[0]
        if t.isalpha() and len(t) <= 2:
            return True
    return False


def build_tech_index(techs: list[str]):
    """기술 스택 검색용 인덱스 생성"""
    single_index = defaultdict(list)  # 단일 토큰 -> [tech]
    multi_index = defaultdict(list)   # 첫 번째 토큰 -> [tech]
    tech_tokens_map = {}

    for tech in techs:
        tokens = TOKEN_RE.findall(tech.lower())
        if not tokens:
            continue
        tech_tokens_map[tech] = tokens

        if len(tokens) == 1:
            single_index[tokens[0]].append(tech)
        else:
            multi_index[tokens[0]].append(tech)

    return single_index, multi_index, tech_tokens_map


def find_techs_in_text(text: str, single_index, multi_index, tech_tokens_map) -> set:
    """텍스트에서 기술 스택 찾기"""
    found_techs = set()
    text_lower = normalize_text(text)
    text_tokens = TOKEN_RE.findall(text_lower)

    for i, token in enumerate(text_tokens):
        # 단일 토큰 기술 매칭
        for tech in single_index.get(token, []):
            if not is_noise_tech(tech.lower()):
                found_techs.add(tech)

        # 다중 토큰 기술 매칭
        for tech in multi_index.get(token, []):
            tech_tokens = tech_tokens_map.get(tech, [])
            if not tech_tokens:
                continue
            # 연속 토큰 매칭 확인
            L = len(tech_tokens)
            if i + L <= len(text_tokens):
                if text_tokens[i:i + L] == tech_tokens:
                    found_techs.add(tech)

    return found_techs


class Command(BaseCommand):
    help = '원티드 IT 개발 직군 공고 수집 (경력 추출 및 기술 매칭 포함)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', 
            type=int, 
            default=1000, 
            help='수집할 공고의 최대 개수 (0 입력 시 전체 수집, 기본값: 1000)'
        )
        # [주석 처리] skill_tags 방식은 일치율이 낮아 기본적으로 본문 분석 사용
        # parser.add_argument(
        #     '--use-body-analysis',
        #     action='store_true',
        #     help='skill_tags 대신 본문 분석으로 기술 스택 추출'
        # )
        # parser.add_argument(
        #     '--combine-methods',
        #     action='store_true',
        #     help='skill_tags와 본문 분석을 병행하여 기술 스택 추출'
        # )
    # [추가됨] 카카오 좌표 -> 주소 변환 함수
    def get_region_from_kakao(self, lat, lng, api_key):
        url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
        headers = {"Authorization": f"KakaoAK {api_key}"}
        params = {"x": lng, "y": lat} # x:경도, y:위도

        try:
            # # 1. 요청 전 파라미터 확인
            # print(f"\n[DEBUG] 요청 좌표 - lat: {lat}, lng: {lng}")
            
            response = requests.get(url, headers=headers, params=params, timeout=3)
            
            # # 2. 상태 코드 및 응답 본문 확인
            # print(f"[DEBUG] 상태 코드: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[DEBUG] 에러 메시지: {response.text}") 
                return None

            data = response.json()
            documents = data.get('documents', [])

            # # 3. 결과 개수 확인
            # print(f"[DEBUG] 검색된 행정구역 개수: {len(documents)}")

            for doc in documents:
                if doc['region_type'] == 'H':
                    return {
                        'city': doc['region_1depth_name'],
                        'district': doc['region_2depth_name']
                    }
            
            if documents:
                return {
                    'city': documents[0]['region_1depth_name'],
                    'district': documents[0]['region_2depth_name']
                }
                
        except Exception as e:
            print(f"[DEBUG] 예외 발생: {str(e)}")
        return None

    def handle(self, *args, **options):
        KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
        if not KAKAO_REST_API_KEY:
            self.stdout.write(self.style.ERROR("[FATAL] KAKAO_REST_API_KEY가 환경 변수에 설정되지 않았습니다."))
            return
        target_count = options['count']
        
        # [주석 처리] skill_tags 방식은 일치율이 낮아 기본적으로 본문 분석만 사용
        # use_body_analysis = options.get('use_body_analysis', False)
        # combine_methods = options.get('combine_methods', False)
        
        base_url = "https://www.wanted.co.kr/api/v4/jobs"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.wanted.co.kr/wdlist/518"
        }

        # [성능 최적화] 우리 DB에 있는 기술 스택 이름만 메모리에 로드
        existing_stacks = list(TechStack.objects.values_list('name', flat=True))
        self.stdout.write(self.style.SUCCESS(f"[INFO] 현재 DB 내 기술 스택 {len(existing_stacks)}개를 로드했습니다."))
        
        # 본문 분석용 인덱스 생성 (기본 모드)
        single_index, multi_index, tech_tokens_map = build_tech_index(existing_stacks)
        self.stdout.write(self.style.SUCCESS(f"[INFO] 본문 분석용 인덱스 생성 완료"))
        self.stdout.write(self.style.WARNING("[MODE] 본문 분석 모드 (기본)"))

        limit = 50
        offset = 0
        total_collected = 0

        while True:
            if target_count > 0 and total_collected >= target_count:
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] 목표 개수({target_count}개) 도달."))
                break

            params = {
                "country": "kr",
                "tag_type_ids": 518,
                "job_sort": "job.latest_order",
                "locations": "all",
                "years": -1,
                "limit": limit,
                "offset": offset
            }

            try:
                response = requests.get(base_url, params=params, headers=headers)
                if response.status_code != 200: break
                
                jobs_data = response.json().get('data', [])
                if not jobs_data: break

                for job in jobs_data:
                    if target_count > 0 and total_collected >= target_count: break
                    
                    wanted_job_id = job.get('id')
                    try:
                        company_info = job.get('company') or {}
                        corp_name = company_info.get('name')
                        if not wanted_job_id or not corp_name: continue

                        # 상세 데이터 가져오기
                        detail_url = f"https://www.wanted.co.kr/api/v4/jobs/{wanted_job_id}"
                        detail_res = requests.get(detail_url, headers=headers)
                        if detail_res.status_code != 200: continue
                        
                        detail_data = detail_res.json()
                        job_detail = detail_data.get('job') or {}

                        # 1. 경력 정보 추출
                        annual_from = job_detail.get('annual_from', 0)
                        annual_to = job_detail.get('annual_to', 0)
                        is_newbie = job_detail.get('is_newbie', False)
                        employment_type = job_detail.get('employment_type', '') # 인턴 여부 확인

                        if employment_type == 'intern':
                            # 인턴은 경력과 무관하게 신입급(0년)으로 취급
                            min_val = 0
                            max_val = 0
                            career_str = "인턴"
                        elif is_newbie:
                            min_val = 0
                            max_val = annual_to if annual_to > 0 else 0
                            career_str = "신입" if annual_to == 0 else f"신입 ~ {annual_to}년"
                        elif annual_from > 0:
                            min_val = annual_from
                            max_val = annual_to if annual_to > 0 else 100 # 상한선 없으면 100
                            career_str = f"{annual_from}년 이상" if annual_to == 0 else f"{annual_from} ~ {annual_to}년"
                        else:
                            # 모든 조건에 해당하지 않는 경우 진정한 의미의 '경력 무관'
                            min_val = 0
                            max_val = 100
                            career_str = "경력 무관"
                        # [최적화 핵심] 1. DB에 이미 존재하는 기업인지 먼저 확인
                        # 이름으로 기업 검색
                        existing_corp = Corp.objects.filter(name=corp_name).first()
                        
                        # 변수 초기화
                        city_name = ""
                        district_name = ""
                        use_api = True # API 호출 여부 플래그
                        # 2. 이미 DB에 있고, '구/군' 정보까지 완벽하다면? -> 그대로 사용!
                        if existing_corp and existing_corp.region_district:
                            city_name = existing_corp.region_city
                            district_name = existing_corp.region_district
                            lat = existing_corp.latitude
                            lng = existing_corp.longitude
                            use_api = False # API 호출 스킵
                            # self.stdout.write(f"   [Skip API] DB 캐시 사용: {corp_name}")
                        # 3. DB에 없거나 정보가 부족할 때만 -> 주소 파싱 및 API 로직 실행
                        if use_api:
                            address_info = job_detail.get('address') or {}
                            geo_location = (address_info.get('geo_location') or {}).get('n_location') or {}
                            location_inner = (address_info.get('geo_location') or {}).get('location') or {}
                            
                            lat = location_inner.get('lat') or geo_location.get('lat')
                            lng = location_inner.get('lng') or geo_location.get('lng')

                            # 1차: 텍스트 파싱
                            city_name = address_info.get('location', "")
                            district_name = address_info.get('district', "")

                            # 2차: 카카오 API 호출 (정보가 비어있고 좌표가 있을 때만)
                            if not district_name and lat and lng:
                                # .env에서 불러온 키 사용
                                region_data = self.get_region_from_kakao(lat, lng, KAKAO_REST_API_KEY)
                                if region_data:
                                    city_name = region_data['city'][:2]
                                    district_name = region_data['district']
                                    self.stdout.write(self.style.SUCCESS(f"   [API 호출] 신규 주소 변환: {city_name} {district_name}"))            
                        # # 2. 주소 및 본문
                        # address_info = job_detail.get('address') or {}
                        # geo_location = (address_info.get('geo_location') or {}).get('n_location') or {}
                        # location_inner = (address_info.get('geo_location') or {}).get('location') or {}

                        # # API마다 구조가 조금씩 다를 수 있어 안전하게 추출
                        # lat = location_inner.get('lat') or geo_location.get('lat')
                        # lng = location_inner.get('lng') or geo_location.get('lng')

                        # # 1차 주소 문자열 파싱 (시/도, 구/군 분리)
                        # city_name = address_info.get('location', "")
                        # district_name = address_info.get('district', "")
                        # # 2차 시도: 구/군 정보가 비어있고 좌표가 있으면 카카오 API 호출
                        # if not district_name and lat and lng:
                        #     self.stdout.write(f"   [API 호출] 지역 정보 누락 -> 카카오 좌표 변환 시도...")
                        #     region_data = self.get_region_from_kakao(lat, lng, KAKAO_REST_API_KEY)
                            
                        #     if region_data:
                        #         city_name = region_data['city'][:2] # "서울특별시" -> "서울"
                        #         district_name = region_data['district'] # "강서구"
                        #         self.stdout.write(self.style.SUCCESS(f"   -> 성공: {city_name} {district_name}"))
                        #     else:
                        #         self.stdout.write(self.style.WARNING("   -> 실패: API 응답 없음"))


                        detail_content = job_detail.get('detail') or {}
                        full_description = (
                            f"## 주요업무\n{detail_content.get('main_tasks', '')}\n\n"
                            f"## 자격요건\n{detail_content.get('requirements', '')}\n\n"
                            f"## 우대사항\n{detail_content.get('preferred_points', '')}"
                        )
                        
                        # [주석 처리] skill_tags 방식 사용하지 않음
                        # skill_tags = job_detail.get('skill_tags', [])
                        logo_thumb = (job.get('logo_img') or {}).get('thumb')

                        with transaction.atomic():
                            # 1. 기업 정보 저장
                            corp, _ = Corp.objects.update_or_create(
                                name=corp_name,
                                defaults={
                                    'logo_url': logo_thumb,
                                    'address': address_info.get('full_location'),
                                    'region_city': city_name,        # 파싱한 시/도 저장
                                    'region_district': district_name, # 파싱한 구/군 저장
                                    'latitude': lat,
                                    'longitude': lng,
                                    'is_deleted': False
                                }
                            )

                            # 2. 공고 정보 저장 (stack_count 강제 할당으로 에러 방지)
                            job_obj, _ = JobPosting.objects.update_or_create(
                                posting_number=wanted_job_id,
                                defaults={
                                    'corp': corp,
                                    'title': job.get('position'),
                                    'url': f"https://www.wanted.co.kr/wd/{wanted_job_id}",
                                    'description': full_description,
                                    'expiry_date': job_detail.get('due_time'),
                                    'career': career_str, 
                                    'min_career': min_val, # 정제된 최소 경력 저장
                                    'max_career': max_val, # 정제된 최대 경력 저장
                                    #'stack_count': 0,  # [핵심] DB의 NOT NULL 제약조건 통과를 위해 0 할당
                                    'is_deleted': False 
                                }
                            )

                            # --- [3. 기술 스택 연결 (본문 분석 방식)] ---
                            JobPostingStack.objects.filter(job_posting=job_obj).delete()
                            
                            # 본문 분석으로 기술 스택 추출
                            matched_techs = find_techs_in_text(
                                full_description, 
                                single_index, 
                                multi_index, 
                                tech_tokens_map
                            )
                            
                            # [주석 처리] skill_tags 방식 - 일치율이 낮아 사용하지 않음
                            # for skill in skill_tags:
                            #     skill_name = skill.get('title')
                            #     if not skill_name: 
                            #         continue
                            #     # Fuzzy Matching 실행
                            #     match = process.extractOne(skill_name, existing_stacks, score_cutoff=85)
                            #     if match:
                            #         matched_techs.add(match[0])
                            
                            # 매칭된 기술 스택 저장
                            for tech_name in matched_techs:
                                try:
                                    ts = TechStack.objects.get(name=tech_name)
                                    JobPostingStack.objects.create(
                                        job_posting=job_obj, 
                                        tech_stack=ts
                                    )
                                except TechStack.DoesNotExist:
                                    pass  # DB에 없는 기술 스택은 스킵
                                                                            
                            total_collected += 1
                        if total_collected % 10 == 0:
                            self.stdout.write(f"[PROGRESS] {total_collected}개 공고 처리 완료...")

                    except Exception as inner_e:
                        #self.stdout.write(self.style.ERROR(f"[ERROR] ID:{wanted_job_id} 처리 실패: {str(inner_e)}"))
                        print("유니크 설정으로 인해 중복 스킵!")
                        continue
                
                offset += limit
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FATAL] 오류 발생: {str(e)}"))
                offset += limit

        self.stdout.write(self.style.SUCCESS(f"[FINISH] 최종 완료! 총 {total_collected}건의 공고가 동기화되었습니다."))