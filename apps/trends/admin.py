"""
트렌드 관리자 설정
"""

from django.contrib import admin
from .models import Category, TechStack, TechTrend, Article, TechBookmark


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'is_deleted']
    search_fields = ['name']


@admin.register(TechStack)
class TechStackAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_categories', 'created_at', 'is_deleted']
    search_fields = ['name']
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
    list_display = ['id', 'source', 'stack_count', 'created_at']
    list_filter = ['source']


@admin.register(TechBookmark)
class TechBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'tech_stack', 'created_at']
    list_filter = []
