"""
면접 URL 설정
"""

from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    # 면접 질문
    path('questions/', views.InterviewQuestionListView.as_view(), name='question_list'),
    path('questions/<int:pk>/', views.InterviewQuestionDetailView.as_view(), name='question_detail'),
    path('questions/by-tech/<int:tech_stack_id>/', views.QuestionsByTechView.as_view(), name='questions_by_tech'),
    path('questions/generate/', views.GenerateQuestionsView.as_view(), name='generate_questions'),

    # 면접 연습
    path('practice/', views.InterviewPracticeListCreateView.as_view(), name='practice_list_create'),
    path('practice/<int:pk>/', views.InterviewPracticeDetailView.as_view(), name='practice_detail'),

    # 답변 제출 및 피드백
    path('practice/<int:practice_id>/answer/', views.SubmitAnswerView.as_view(), name='submit_answer'),
]
