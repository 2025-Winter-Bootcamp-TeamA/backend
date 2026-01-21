"""
트렌드 URL 설정
"""

from django.urls import path
from . import views

app_name = 'trends'

urlpatterns = [
    # 기술 스택
    path('tech-stacks/', views.TechStackListView.as_view(), name='tech_stack_list'),
    path('tech-stacks/<int:pk>/', views.TechStackDetailView.as_view(), name='tech_stack_detail'),
    path('tech-stacks/<int:tech_stack_id>/docs/', views.TechDocsURLView.as_view(), name='tech_docs_url'),

    # 카테고리
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:category_id>/', views.CategoryTechStackListView.as_view(), name='category_tech_stack_list'),
    path('categories/<int:category_id>/job-posting', views.CategoryJobPostingListView.as_view(), name='category_job_posting_list'),
    path('categories/<int:category_id>/articles', views.CategoryArticleListView.as_view(), name='category_article_list'),

    # 트렌드
    path('', views.TechTrendListView.as_view(), name='trend_list'),
    path('ranking/', views.TrendRankingView.as_view(), name='trend_ranking'),

    # 즐겨찾기
    path('tech-bookmarks/', views.TechBookmarkListCreateAPIView.as_view(), name='tech_bookmarks_list_create'),
    path('tech-bookmarks/<int:tech_bookmark_id>/', views.TechBookmarkDeleteAPIView.as_view(), name='tech_bookmarks_delete'),
    
    # 기술 스택 관계
    path('tech-stacks/<int:id>/relations/', views.TechStackRelationsView.as_view(), name='tech_stack_relations'),
]
