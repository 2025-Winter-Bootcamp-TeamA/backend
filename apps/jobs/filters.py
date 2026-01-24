# apps/jobs/filters.py

import django_filters
from .models import JobPosting

class JobPostingFilter(django_filters.FilterSet):
    # 1. 기업 필터 (새로 추가됨)
    # URL에서 ?corp_id=1 처럼 특정 기업만 콕 집어서 볼 때 사용
    corp_id = django_filters.NumberFilter(field_name='corp__id')
    # URL에서 ?corp_name=삼성 처럼 기업 이름으로 검색할 때 사용 (선택 사항)
    corp_name = django_filters.CharFilter(field_name='corp__corp_name', lookup_expr='icontains')

    # 2. 지역 필터 (기존 유지)
    city = django_filters.CharFilter(field_name='corp__region_city', lookup_expr='icontains')
    district = django_filters.CharFilter(field_name='corp__region_district', lookup_expr='icontains')

    # 3. 직무 및 키워드 검색 (기존 유지)
    search = django_filters.CharFilter(method='filter_search')

    # 4. 경력 필터 (기존 유지)
    # ?career_year=3 -> 경력 3년차가 지원 가능한 공고 필터링
    career_year = django_filters.NumberFilter(method='filter_by_career')

    class Meta:
        model = JobPosting
        # 필드 목록에 corp_id와 corp_name을 꼭 추가해야 합니다.
        fields = ['corp_id', 'corp_name', 'city', 'district', 'career_year']

    def filter_search(self, queryset, name, value):
        return queryset.filter(title__icontains=value) | queryset.filter(description__icontains=value)

    def filter_by_career(self, queryset, name, value):
        # min_career <= value <= max_career (범위 검색)
        return queryset.filter(min_career__lte=value, max_career__gte=value)