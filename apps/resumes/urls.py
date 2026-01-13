"""
이력서 URL 설정
"""

from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    # 이력서 CRUD
    path('', views.ResumeListCreateView.as_view(), name='resume_list_create'),
    path('<int:pk>/', views.ResumeDetailView.as_view(), name='resume_detail'),

    # 이력서 분석
    path('<int:pk>/analyze/', views.ResumeAnalyzeView.as_view(), name='resume_analyze'),

    # 채용 공고 매칭
    path('<int:pk>/match/<int:job_posting_id>/', views.ResumeMatchingView.as_view(), name='resume_matching'),
    
    # 매칭 목록 및 상세
    path('matchings/', views.ResumeMatchingListView.as_view(), name='resume_matching_list'),
    path('matchings/<int:pk>/', views.ResumeMatchingDetailView.as_view(), name='resume_matching_detail'),
]
