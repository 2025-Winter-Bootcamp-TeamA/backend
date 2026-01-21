"""
채용 공고 URL 설정
"""

from django.urls import path
from . import views

app_name = 'corps'

urlpatterns = [
    # 기업
    # path('corps/', views.CorpListView.as_view(), name='corp_list'),
    # path('corps/<int:pk>/', views.CorpDetailView.as_view(), name='corp_detail'),
    path('corp-bookmarks/', views.CorpBookmarkListView.as_view(), name='corp_bookmark_list'), #즐겨찾기 추가,조회 
    path('corp-bookmarks/<int:corp_bookmark_id>/', views.CorpBookmarkDetailView.as_view(), name='corp_bookmark_detail'), #즐겨찾기 삭제

    # path('corps/<int:corp_id>/bookmark/', views.CorpBookmarkToggleView.as_view(), name='corp_bookmark_toggle'),
    path('corps/', views.CorpListView.as_view(), name='corp_list'), #기업 검색
    path('corps/<int:pk>/', views.CorpDetailView.as_view(), name='corp_detail'), #기업 목록 검색
    
    #path('corps/bookmarks/', views.CorpBookmarkListView.as_view(), name='corp_bookmark_list'),
    #path('<int:corp_id>/bookmark/', views.CorpBookmarkToggleView.as_view(), name='corp_bookmark_toggle'),

    # 채용 공고
    path('corps/<int:corp_id>/job-postings/', views.JobPostingListView.as_view(), name='job_posting_list'), #채용공고 조회
    #path('<int:pk>/', views.JobPostingDetailView.as_view(), name='job_posting_detail'),
    path('by-tech/<int:tech_stack_id>/', views.JobPostingByTechView.as_view(), name='job_posting_by_tech'),
]
