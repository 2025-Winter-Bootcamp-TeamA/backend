import requests
import time
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.jobs.models import Corp, JobPosting, JobPostingStack
from apps.trends.models import TechStack
from fuzzywuzzy import process  # 문자열 유사도 매칭을 위해 필수

class Command(BaseCommand):
    help = '원티드 IT 개발 직군 공고 수집 (경력 추출 및 Fuzzy 기술 매칭 포함)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', 
            type=int, 
            default=1000, 
            help='수집할 공고의 최대 개수 (0 입력 시 전체 수집, 기본값: 1000)'
        )
    
    # [추가됨] 카카오 좌표 -> 주소 변환 함수
    def get_region_from_kakao(self, lat, lng, api_key):
        url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
        headers = {"Authorization": f"KakaoAK {api_key}"}
        params = {"x": lng, "y": lat} # x:경도, y:위도

        try:
            response = requests.get(url, headers=headers, params=params, timeout=3)
            
            if response.status_code != 200:
                print(f"[DEBUG] 에러 메시지: {response.text}") 
                return None

            data = response.json()
            documents = data.get('documents', [])

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
        base_url = "https://www.wanted.co.kr/api/v4/jobs"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.wanted.co.kr/wdlist/518"
        }

        # [성능 최적화] 우리 DB에 있는 기술 스택 이름만 메모리에 로드
        existing_stacks = list(TechStack.objects.values_list('name', flat=True))
        self.stdout.write(self.style.SUCCESS(f"[INFO] 현재 DB 내 기술 스택 {len(existing_stacks)}개를 로드했습니다."))

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

                        detail_content = job_detail.get('detail') or {}
                        full_description = (
                            f"## 주요업무\n{detail_content.get('main_tasks', '')}\n\n"
                            f"## 자격요건\n{detail_content.get('requirements', '')}\n\n"
                            f"## 우대사항\n{detail_content.get('preferred_points', '')}"
                        )
                        
                        skill_tags = job_detail.get('skill_tags', [])
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

                            # 2. 공고 정보 저장
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
                                    'is_deleted': False 
                                }
                            )

                            # --- [3. Fuzzy Matching 및 언급량 계산 기반 기술 스택 연결] ---
                            JobPostingStack.objects.filter(job_posting=job_obj).delete()

                            # 본문 텍스트를 소문자로 변환하여 대소문자 구분 없이 카운트 준비
                            description_lower = full_description.lower()

                            for skill in skill_tags:
                                skill_name = skill.get('title')
                                if not skill_name: continue
                                
                                # 1. Fuzzy Matching 실행
                                match = process.extractOne(skill_name, existing_stacks, score_cutoff=85)

                                if match:
                                    target_name = match[0]
                                    ts = TechStack.objects.get(name=target_name)
                                    
                                    # 3. 데이터 저장
                                    JobPostingStack.objects.create(
                                        job_posting=job_obj, 
                                        tech_stack=ts
                                    )
                                else:
                                    self.stdout.write(self.style.WARNING(f"   [Skip] 신규 기술 발견: {skill_name}"))
                                                                            
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
