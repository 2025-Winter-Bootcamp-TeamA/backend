from django.contrib import admin
from .models import Resume, ResumeStack, ResumeMatching

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at', 'is_deleted']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['title', 'user__email']

@admin.register(ResumeStack)
class ResumeStackAdmin(admin.ModelAdmin):
    list_display = ['id', 'resume', 'tech_stack']
    list_filter = ['tech_stack']

@admin.register(ResumeMatching)
class ResumeMatchingAdmin(admin.ModelAdmin):
    list_display = ['id', 'resume', 'job_posting', 'score', 'created_at']
    list_filter = ['is_deleted', 'created_at']