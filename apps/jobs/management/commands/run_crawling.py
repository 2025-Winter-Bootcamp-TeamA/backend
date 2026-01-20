import requests
import time
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

    def handle(self, *args, **options):
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

                        if is_newbie and annual_to == 0:
                            career_str = "신입"
                        elif is_newbie and annual_to > 0:
                            career_str = f"신입 ~ {annual_to}년"
                        elif annual_from > 0 and annual_to > 0:
                            career_str = f"{annual_from}년차" if annual_from == annual_to else f"{annual_from} ~ {annual_to}년"
                        elif annual_from > 0:
                            career_str = f"{annual_from}년 이상"
                        else:
                            career_str = "경력 무관"

                        # 2. 주소 및 본문
                        address_info = job_detail.get('address') or {}
                        geo_location = (address_info.get('geo_location') or {}).get('n_location') or {}
                        
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
                                    'latitude': geo_location.get('lat'),
                                    'longitude': geo_location.get('lng'),
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
                                    #'stack_count': 0,  # [핵심] DB의 NOT NULL 제약조건 통과를 위해 0 할당
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
                                    
                                    # # 2. 언급량(Count) 계산
                                    # # 본문에서 해당 기술명이 몇 번 등장하는지 계산 (최소 1번은 태그에 있었으므로 1 보장)
                                    # mention_count = description_lower.count(target_name.lower())
                                    # if mention_count == 0:
                                    #     mention_count = 1  # 태그에는 있지만 본문 설명에는 직접 언급되지 않은 경우
                                    
                                    # 3. 데이터 저장
                                    JobPostingStack.objects.create(
                                        job_posting=job_obj, 
                                        tech_stack=ts, 
                                        #job_stack_count=mention_count  # 계산된 언급량 반영
                                    )
                                    
                                    # self.stdout.write(f"   [Matched] {target_name} ({mention_count}회 언급)")
                                else:
                                    self.stdout.write(self.style.WARNING(f"   [Skip] 신규 기술 발견: {skill_name}"))
                                                                            
                                total_collected += 1
                        if total_collected % 10 == 0:
                            self.stdout.write(f"[PROGRESS] {total_collected}개 공고 처리 완료...")

                    except Exception as inner_e:
                        self.stdout.write(self.style.ERROR(f"[ERROR] ID:{wanted_job_id} 처리 실패: {str(inner_e)}"))
                        continue
                
                offset += limit
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FATAL] 오류 발생: {str(e)}"))
                offset += limit

        self.stdout.write(self.style.SUCCESS(f"[FINISH] 최종 완료! 총 {total_collected}건의 공고가 동기화되었습니다."))