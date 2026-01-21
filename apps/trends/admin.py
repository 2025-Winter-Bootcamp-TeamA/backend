"""
트렌드 관리자 설정
"""

from django.contrib import admin
from .models import Category, TechStack, TechTrend, Article, TechBookmark, ArticleStack


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'is_deleted']
    search_fields = ['name']


@admin.register(TechStack)
class TechStackAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_categories', 'article_stack_count', 'created_at', 'is_deleted']
    search_fields = ['name']
    ordering = ('-article_stack_count',) 
    def get_categories(self, obj):
        categories = obj.category_relations.all()
        return ", ".join([rel.category.name for rel in categories])
    get_categories.short_description = '카테고리'
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('category_relations__category')

@admin.register(TechTrend)
class TechTrendAdmin(admin.ModelAdmin):
    list_display = ['tech_stack', 'mention_count', 'change_rate', 'reference_date']
    list_filter = ['reference_date', 'tech_stack']
    ordering = ['-reference_date', '-mention_count']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['id', 'view_count', 'source', 'url', 'created_at']
    list_filter = ['source']


@admin.register(TechBookmark)
class TechBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'tech_stack', 'created_at']
    list_filter = []

@admin.register(ArticleStack) 
class ArticleStackAdmin(admin.ModelAdmin): 
    list_display = ['article', 'tech_stack', 'count', 'created_at', 'is_deleted'] 
    list_filter = ['tech_stack'] 
    search_fields = ['article__url', 'tech_stack__name'] 