# apps/jobs/filters.py

import django_filters
from django.db.models import Q  
from .models import JobPosting

class JobPostingFilter(django_filters.FilterSet):
    # 1. 기업 필터 (새로 추가됨)
    # URL에서 ?corp_id=1 처럼 특정 기업만 콕 집어서 볼 때 사용
    corp_id = django_filters.NumberFilter(field_name='corp__id')
    # URL에서 ?corp_name=삼성 처럼 기업 이름으로 검색할 때 사용 (선택 사항)
    corp_name = django_filters.CharFilter(field_name='corp__name', lookup_expr='icontains')

    # 2. 지역 필터 (기존 유지)
    city = django_filters.CharFilter(field_name='corp__region_city', lookup_expr='icontains')
    district = django_filters.CharFilter(field_name='corp__region_district', lookup_expr='icontains')

    # 3.통합검색 직무 및 키워드 검색 (기존 유지)
    search = django_filters.CharFilter(method='filter_search')

    # 3. [추가됨] 직무(제목) 및 기술 스택 필터
    # 공고 제목에 '백엔드', '프론트' 등이 포함된 것을 찾습니다.
    job_title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')

    # 4. 경력 필터 (기존 유지)
    # ?career_year=3 -> 경력 3년차가 지원 가능한 공고 필터링
    career_year = django_filters.NumberFilter(method='filter_by_career')

    class Meta:
        model = JobPosting
        fields = ['corp_id', 'corp_name', 'city', 'district', 'career_year','job_title', 'search']

    def filter_search(self, queryset, name, value):
        """
        [개선됨] Q 객체를 사용하여 제목, 설명, 기업명을 한 번에 검색합니다.
        (성능 및 안정성 향상)
        """
        return queryset.filter(
            Q(title__icontains=value) | 
            Q(description__icontains=value) | 
            Q(corp__name__icontains=value)
        )

    def filter_by_career(self, queryset, name, value):
        """
        [디버깅 모드] 경력 필터링 로직
        """
        # 1. 입력값 확인
        print(f"\n[DEBUG] 사용자 입력 연차: {value} (Type: {type(value)})")

        if value is None:
            return queryset

        # 2. 필터링 전, 해당 공고의 실제 DB 값 확인 (ID와 경력값 출력)
        # (너무 많이 출력되면 보기 힘들므로 상위 5개만 확인)
        print("[DEBUG] DB 데이터 샘플 확인 (필터링 전):")
        for job in queryset[:5]:
            print(f" - 공고 ID: {job.id} | 기업: {job.corp.name} | Min: {job.min_career} | Max: {job.max_career}")

        # 3. 실제 필터링 적용
        # Q객체 사용: (최대 경력이 내 연차보다 크거나) OR (0이거나) OR (NULL이거나)
        filtered_qs = queryset.filter(
            min_career__lte=value
        ).filter(
            Q(max_career__gte=value) | Q(max_career=0) | Q(max_career__isnull=True)
        )

        # 4. 결과 확인
        print(f"[DEBUG] 필터링 후 남은 공고 개수: {filtered_qs.count()}")
        print(f"[DEBUG] 생성된 SQL 쿼리: {filtered_qs.query}\n")
        
        return filtered_qs