"""
채용 공고 관리자 설정
"""

from django.contrib import admin
from .models import Corp, JobPosting, JobPostingStack, CorpBookmark


@admin.register(Corp)
class CorpAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at', 'is_deleted']
    search_fields = ['name', 'address']


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['corp', 'title', 'stack_count', 'created_at']
    list_filter = ['corp', 'created_at']
    search_fields = ['title', 'corp__name']


@admin.register(JobPostingStack)
class JobPostingStackAdmin(admin.ModelAdmin):
    list_display = ['job_posting', 'tech_stack', 'created_at']
    list_filter = ['tech_stack']


@admin.register(CorpBookmark)
class CorpBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'corp', 'created_at', 'is_deleted']
    list_filter = ['is_deleted']
