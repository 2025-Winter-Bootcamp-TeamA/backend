"""
채용 공고 URL 설정
"""

from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # 기업
    path('corps/', views.CorpListView.as_view(), name='corp_list'),
    path('corps/<int:pk>/', views.CorpDetailView.as_view(), name='corp_detail'),
    path('corps/bookmarks/', views.CorpBookmarkListView.as_view(), name='corp_bookmark_list'),
    path('corps/<int:corp_id>/bookmark/', views.CorpBookmarkToggleView.as_view(), name='corp_bookmark_toggle'),

    # 채용 공고
    path('', views.JobPostingListView.as_view(), name='job_posting_list'),
    path('<int:pk>/', views.JobPostingDetailView.as_view(), name='job_posting_detail'),
    path('by-tech/<int:tech_stack_id>/', views.JobPostingByTechView.as_view(), name='job_posting_by_tech'),
]
