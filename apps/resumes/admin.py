from django.contrib import admin
from .models import Resume, ResumeStack, ResumeMatching, WorkExperience, ProjectExperience

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

@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ['id', 'resume', 'organization', 'details']
    search_fields = ['organization', 'details']

@admin.register(ProjectExperience)
class ProjectExperienceAdmin(admin.ModelAdmin):
    list_display = ['id', 'resume', 'project_name', 'context', 'details']
    search_fields = ['project_name', 'context', 'details']