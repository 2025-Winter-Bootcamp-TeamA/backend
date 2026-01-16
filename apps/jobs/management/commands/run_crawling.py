import requests
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.jobs.models import Corp, JobPosting, JobPostingStack
from apps.trends.models import TechStack 

class Command(BaseCommand):
    help = '원티드 IT 개발 직군 공고 수집 (개수 지정 가능, 기본값 1000개)'

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

        if target_count == 0:
            self.stdout.write(self.style.WARNING("[INFO] 목표: 전체 공고를 끝까지 수집합니다."))
        else:
            self.stdout.write(self.style.WARNING(f"[INFO] 목표: 최신 공고 최대 {target_count}개를 수집합니다."))

        limit = 50
        offset = 0
        total_collected = 0

        while True:
            if target_count > 0 and total_collected >= target_count:
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] 목표 개수({target_count}개)에 도달하여 수집을 종료합니다."))
                break

            self.stdout.write(f"[INFO] 목록 가져오는 중... (Offset: {offset}, 현재 수집: {total_collected}개)")

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
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"[ERROR] 목록 API 호출 실패: {response.status_code}"))
                    break

                jobs_data = response.json().get('data', [])
                
                if not jobs_data:
                    self.stdout.write(self.style.SUCCESS("[SUCCESS] 더 이상 가져올 공고가 없습니다 (목록 끝)."))
                    break

                for job in jobs_data:
                    if target_count > 0 and total_collected >= target_count:
                        break
                    
                    # [수정] 개별 공고 처리 중 에러가 나도 멈추지 않도록 try-except를 안으로 넣음
                    try:
                        wanted_job_id = job.get('id')
                        # [수정] company가 None일 경우 방어 로직 추가
                        company_info = job.get('company') or {}
                        corp_name = company_info.get('name')
                        
                        if not wanted_job_id or not corp_name:
                            continue

                        detail_url = f"https://www.wanted.co.kr/api/v4/jobs/{wanted_job_id}"
                        detail_res = requests.get(detail_url, headers=headers)
                        
                        if detail_res.status_code != 200:
                            continue
                        
                        detail_data = detail_res.json()
                        job_detail = detail_data.get('job') or {} # [수정] job이 None이면 빈 딕셔너리로

                        # 1. 주소 및 좌표 추출 (가장 에러가 많이 나는 부분 방어)
                        address_info = job_detail.get('address') or {} # [수정] None 방지
                        full_address = address_info.get('full_location')
                        geo_location = (address_info.get('geo_location') or {}).get('n_location') or {}
                        lat = geo_location.get('lat')
                        lng = geo_location.get('lng')

                        # 2. 본문 내용
                        detail_content = job_detail.get('detail') or {}
                        full_description = (
                            f"## 주요업무\n{detail_content.get('main_tasks', '')}\n\n"
                            f"## 자격요건\n{detail_content.get('requirements', '')}\n\n"
                            f"## 우대사항\n{detail_content.get('preferred_points', '')}"
                        )
                        
                        due_time = job_detail.get('due_time') 
                        career_str = "채용 상세 참조"
                        skill_tags = job_detail.get('skill_tags', [])

                        # [수정] 로고 URL 추출 시에도 None 방지
                        logo_img = job.get('logo_img') or {}
                        logo_thumb = logo_img.get('thumb')

                        with transaction.atomic():
                            corp, _ = Corp.objects.update_or_create(
                                name=corp_name,
                                defaults={
                                    'logo_url': logo_thumb,
                                    'address': full_address,
                                    'latitude': lat,
                                    'longitude': lng,
                                    'is_deleted': False
                                }
                            )

                            job_obj, created = JobPosting.objects.update_or_create(
                                posting_number=wanted_job_id,
                                defaults={
                                    'corp': corp,
                                    'title': job.get('position'),
                                    'url': f"https://www.wanted.co.kr/wd/{wanted_job_id}",
                                    'description': full_description,
                                    'expiry_date': due_time,
                                    'career': career_str,
                                    'stack_count': len(skill_tags),
                                    'is_deleted': False 
                                }
                            )

                            JobPostingStack.objects.filter(job_posting=job_obj).delete()
                            for skill in skill_tags:
                                skill_name = skill.get('title')
                                if not skill_name:
                                    continue
                                
                                ts, _ = TechStack.objects.get_or_create(
                                    name=skill_name,
                                    defaults={'is_deleted': False} 
                                )
                                JobPostingStack.objects.create(
                                    job_posting=job_obj, tech_stack=ts, job_stack_count=1 
                                )
                        
                        total_collected += 1
                    
                    except Exception as inner_e:
                        # 개별 공고 수집 실패 시 로그만 남기고 다음 공고로 넘어감 (멈추지 않음!)
                        self.stdout.write(self.style.ERROR(f"[ERROR] 공고(ID:{wanted_job_id}) 처리 중 건너뜀: {str(inner_e)}"))
                        continue
                
                # 다음 페이지로 이동 (여기가 실행되어야 무한루프 안 빠짐)
                offset += limit
                time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FATAL ERROR] 목록 처리 중 치명적 오류: {str(e)}"))
                time.sleep(3)
                # 치명적 오류가 나도 다음 페이지 시도를 위해 offset 증가 (선택사항, 혹은 break)
                offset += limit

        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] 최종 완료! 총 {total_collected}건 수집됨."))