"""
면접 URL 설정
ERD에 면접 관련 테이블이 없으므로, ResumeMatching 기반으로 처리
"""

from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    # 면접 질문 조회 (ResumeMatching 기반)
    path('matchings/<int:matching_id>/question/', views.InterviewQuestionView.as_view(), name='interview_question'),

    # 면접 답변 제출 및 피드백
    path('matchings/<int:matching_id>/answer/', views.SubmitInterviewAnswerView.as_view(), name='submit_interview_answer'),
]
