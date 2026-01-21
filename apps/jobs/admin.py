""" 
#채용 공고 관리자 설정

import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import Corp, JobPosting, JobPostingStack, CorpBookmark

# ✅ 1. 모든 모델에서 공용으로 쓸 CSV 추출 함수 정의
def export_as_csv(modeladmin, request, queryset):
    # 모델의 메타 정보를 가져와서 파일명 자동 생성 (예: corp_export.csv)
    meta = modeladmin.model._meta
    filename = f"{meta.verbose_name_plural}_export.csv"
    
    # 한글 깨짐 방지 (utf-8-sig)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # 모델의 모든 필드명 가져오기 (헤더 생성)
    field_names = [field.name for field in meta.fields]
    writer.writerow(field_names)

    # 데이터 입력
    for obj in queryset:
        row = []
        for field in field_names:
            value = getattr(obj, field)
            # 값이 있으면 문자열로 변환, 없으면 빈 문자열
            row.append(str(value) if value is not None else '') 
        writer.writerow(row)

    return response

# 어드민 페이지 버튼 이름
export_as_csv.short_description = "선택된 데이터 CSV 다운로드"


# ✅ 2. 각 Admin 클래스에 actions 추가 (즐겨찾기 제외)

@admin.register(Corp)
class CorpAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at', 'is_deleted']
    search_fields = ['name', 'address']
    actions = [export_as_csv]  # 👉 추가됨


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['corp', 'title', 'stack_count', 'created_at']
    list_filter = ['corp', 'created_at']
    search_fields = ['title', 'corp__name']
    actions = [export_as_csv]  # 👉 추가됨


@admin.register(JobPostingStack)
class JobPostingStackAdmin(admin.ModelAdmin):
    list_display = ['job_posting', 'tech_stack', 'created_at']
    list_filter = ['tech_stack']
    actions = [export_as_csv]  # 👉 추가됨


@admin.register(CorpBookmark)
class CorpBookmarkAdmin(admin.ModelAdmin):
    # ❌ 여기는 actions를 넣지 않았으므로 다운로드 버튼이 안 뜹니다.
    list_display = ['user', 'corp', 'created_at', 'is_deleted']
    list_filter = ['is_deleted']
"""

from django.contrib import admin
from .models import Corp, JobPosting, JobPostingStack, CorpBookmark


@admin.register(Corp)
class CorpAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at', 'is_deleted','latitude','longitude']
    search_fields = ['name', 'address']


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['corp', 'title', 'created_at','expiry_date','career','posting_number']
    list_filter = ['corp', 'created_at']
    search_fields = ['title', 'corp__name']
    
@admin.register(JobPostingStack)
class JobPostingStackAdmin(admin.ModelAdmin):
    list_display = ['job_posting', 'tech_stack', 'created_at']
    list_filter = ['tech_stack']
    search_fields = ['tech_stack__name']


@admin.register(CorpBookmark)
class CorpBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'corp', 'created_at', 'is_deleted']
    list_filter = ['is_deleted']
 