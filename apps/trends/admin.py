"""
트렌드 관리자 설정
"""

from django.contrib import admin
from .models import Category, TechStack, TechTrend, Article, TechBookmark, TechStackRelationship, ArticleStack

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'is_deleted']
    search_fields = ['name']


@admin.register(TechStack)
class TechStackAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_categories','article_stack_count','job_stack_count',  'created_at', 'is_deleted']
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


@admin.register(TechStackRelationship)
class TechStackRelationshipAdmin(admin.ModelAdmin):
    """기술 스택 관계 관리"""
    list_display = [
        'id',
        'from_tech_stack',
        'to_tech_stack',
        'get_relationship_type_display',
        'weight',
        'is_deleted',
        'created_at'
    ]
    list_filter = [
        'relationship_type',
        'is_deleted',
        'created_at'
    ]
    search_fields = [
        'from_tech_stack__name',
        'to_tech_stack__name'
    ]
    ordering = ['-created_at', 'from_tech_stack__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('from_tech_stack', 'to_tech_stack', 'relationship_type')
        }),
        ('관계 상세', {
            'fields': ('weight', 'is_deleted')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """관계 조회 시 기술 스택 정보를 미리 가져오기"""
        return super().get_queryset(request).select_related(
            'from_tech_stack',
            'to_tech_stack'
        )

@admin.register(ArticleStack) 
class ArticleStackAdmin(admin.ModelAdmin): 
    list_display = ['article', 'tech_stack', 'count', 'created_at', 'is_deleted'] 
    list_filter = ['tech_stack'] 
    search_fields = ['article__url', 'tech_stack__name'] 