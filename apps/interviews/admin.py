"""
면접 관리자 설정
"""

from django.contrib import admin
from .models import InterviewQuestion, InterviewPractice, InterviewAnswer


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['question', 'tech_stack', 'question_type', 'difficulty', 'is_deleted']
    list_filter = ['question_type', 'difficulty', 'tech_stack']
    search_fields = ['question']


@admin.register(InterviewPractice)
class InterviewPracticeAdmin(admin.ModelAdmin):
    list_display = ['user', 'job_posting', 'created_at']
    list_filter = ['created_at']


@admin.register(InterviewAnswer)
class InterviewAnswerAdmin(admin.ModelAdmin):
    list_display = ['practice', 'question', 'score', 'created_at']
    list_filter = ['score']
