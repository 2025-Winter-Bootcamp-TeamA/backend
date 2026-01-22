# apps/jobs/filters.py

import django_filters
from .models import JobPosting

class JobPostingFilter(django_filters.FilterSet):
    # 1. 지역 필터: 기업 모델의 region_city 또는 region_district 필드를 참조합니다.
    city = django_filters.CharFilter(field_name='corp__region_city', lookup_expr='icontains')
    district = django_filters.CharFilter(field_name='corp__region_district', lookup_expr='icontains')

    # 2. 직무 및 키워드 검색: 제목이나 설명에 포함된 단어를 검색합니다.
    search = django_filters.CharFilter(method='filter_search')

    # 3. 경력 필터: 사용자가 입력한 연차가 공고의 [min_career, max_career] 범위에 포함되는지 확인합니다.
    # 예: 사용자가 3을 입력하면, min_career <= 3 이고 max_career >= 3 인 공고를 반환합니다.
    career_year = django_filters.NumberFilter(method='filter_by_career')

    class Meta:
        model = JobPosting
        fields = ['city', 'district', 'career_year']

    def filter_search(self, queryset, name, value):
        # 제목 혹은 상세 설명에서 검색어를 찾습니다.
        return queryset.filter(title__icontains=value) | queryset.filter(description__icontains=value)

    def filter_by_career(self, queryset, name, value):
        # 공고의 최소 경력보다는 크거나 같고, 최대 경력보다는 작거나 같은 범위를 필터링합니다.
        # max_career가 99인 경우(경력 무관 등)도 고려하여 검색합니다.
        return queryset.filter(min_career__lte=value, max_career__gte=value)