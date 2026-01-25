"""
채용 공고 URL 설정
"""

from django.urls import path
from . import views

app_name = 'corps'

urlpatterns = [
    # 채용 공고 (더 구체적인 패턴을 먼저)
    path('corps/<int:corp_id>/job-postings/', views.JobPostingListView.as_view(), name='job_posting_list'),
    path('by-tech/<int:tech_stack_id>/', views.JobPostingByTechView.as_view(), name='job_posting_by_tech'),
    
    # 기업 상세 (더 구체적인 패턴을 먼저)
    path('corps/<int:pk>/', views.CorpDetailView.as_view(), name='corp_detail'),
    
    # 기업 목록 (더 일반적인 패턴)
    path('corps/', views.CorpListView.as_view(), name='corp_list'),

    # 대시보드 통계 (분석된 기업 수, 수집된 공고 수)
    path('stats/', views.JobStatsView.as_view(), name='job_stats'),
    
    # 즐겨찾기
    path('corp-bookmarks/<int:corp_bookmark_id>/', views.CorpBookmarkDetailView.as_view(), name='corp_bookmark_detail'),
    path('corp-bookmarks/', views.CorpBookmarkListView.as_view(), name='corp_bookmark_list'),

    #채용공고 전체 조회(필터링용)
    path('job-postings/', views.JobPostingListView.as_view(), name='job_posting_list_all'), 

]
