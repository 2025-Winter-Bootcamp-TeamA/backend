"""
기술 트렌드 모델 정의
ERD의 tech_stack, tech_trend, category, article 테이블 기반
"""

from django.db import models
from django.conf import settings


class Category(models.Model):
    """
    카테고리 모델
    ERD: category 테이블
    """
    name = models.CharField(
        max_length=255,
        verbose_name='카테고리명'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'category'
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리 목록'

    def __str__(self):
        return self.name


class TechStack(models.Model):
    """
    기술 스택 모델
    ERD: tech_stack 테이블
    """
    name = models.CharField(
        max_length=255,
        verbose_name='기술명'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='기술 설명'
    )
    logo = models.TextField(
        blank=True,
        null=True,
        verbose_name='기술 로고'
    )
    docs_url = models.TextField(
        blank=True,
        null=True,
        verbose_name='문서 URL'
    )
    article_stack_count = models.BigIntegerField(
        default=0,
        verbose_name='게시글 스택 언급량'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'tech_stack'
        verbose_name = '기술 스택'
        verbose_name_plural = '기술 스택 목록'

    def __str__(self):
        return self.name


class CategoryTech(models.Model):
    """
    카테고리-기술 연결 모델
    ERD: category_tech 테이블
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='tech_relations',
        verbose_name='카테고리'
    )
    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='category_relations',
        verbose_name='기술 스택'
    )

    class Meta:
        db_table = 'category_tech'
        verbose_name = '카테고리-기술 연결'
        verbose_name_plural = '카테고리-기술 연결 목록'
        unique_together = ['category', 'tech_stack']


class TechTrend(models.Model):
    """
    기술 트렌드 모델
    ERD: tech_trend 테이블
    """
    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='trends',
        verbose_name='기술 스택'
    )
    trend_from = models.CharField(
        max_length=255,
        verbose_name='트렌드 출처 (키워드)'
    )
    mention_count = models.BigIntegerField(
        default=0,
        verbose_name='언급 수'
    )
    change_rate = models.FloatField(
        default=0.0,
        verbose_name='전주 대비 증가율'
    )
    reference_date = models.DateField(
        verbose_name='기준 날짜'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'tech_trend'
        verbose_name = '기술 트렌드'
        verbose_name_plural = '기술 트렌드 목록'
        ordering = ['-reference_date', '-mention_count']

    def __str__(self):
        return f"{self.tech_stack.name} - {self.reference_date}"


class Article(models.Model):
    """
    게시글/기사 모델
    ERD: article 테이블
    """
    # stack_count = models.BigIntegerField(
    #     default=0,
    #     verbose_name='게시글 언급량'
    # )
    view_count = models.BigIntegerField(
        default=0,
        verbose_name="조회수"
    )
    url = models.TextField(
        unique=True, verbose_name='게시글 URL'
    )
    source = models.TextField(
        verbose_name='게시글 출처'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'article'
        verbose_name = '게시글'
        verbose_name_plural = '게시글 목록'

    def __str__(self):
        return f"Article #{self.id}"


class ArticleStack(models.Model):
    """
    게시글-기술 연결 모델
    ERD: article_stack 테이블
    """
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='tech_stacks',
        verbose_name='게시글'
    )
    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name='기술 스택'
    )
    count = models.IntegerField(
        default=0,
        verbose_name='게시글 스택 언급량'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'article_stack'
        verbose_name = '게시글-기술 연결'
        verbose_name_plural = '게시글-기술 연결 목록'
        unique_together = ['article','tech_stack']


class TechBookmark(models.Model):
    """
    기술 즐겨찾기 모델
    ERD: tech_bookmark 테이블
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tech_bookmarks',
        verbose_name='사용자'
    )
    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name='기술 스택'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    class Meta:
        db_table = 'tech_bookmark'
        verbose_name = '기술 즐겨찾기'
        verbose_name_plural = '기술 즐겨찾기 목록'
        unique_together = ['user', 'tech_stack']


class TechStackRelationship(models.Model):
    """
    기술 스택 간 관계 모델
    ERD: tech_stack_relationship 테이블
    """
    RELATIONSHIP_TYPES = [
        ('synergy_with', '시너지 관계'),
        ('required_infra', '필수 인프라'),
        ('alternative', '대체 기술'),
        ('parent', '부모 기술'),
        ('child', '자식 기술'),
    ]
    
    from_tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='outgoing_relationships',
        verbose_name='출발 기술 스택'
    )
    to_tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='incoming_relationships',
        verbose_name='도착 기술 스택'
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_TYPES,
        verbose_name='관계 유형'
    )
    weight = models.FloatField(
        default=1.0,
        help_text='관계의 강도 (0.0 ~ 1.0)',
        verbose_name='관계 강도'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    class Meta:
        db_table = 'tech_stack_relationship'
        verbose_name = '기술 스택 관계'
        verbose_name_plural = '기술 스택 관계 목록'
        unique_together = ['from_tech_stack', 'to_tech_stack', 'relationship_type']
        indexes = [
            models.Index(fields=['from_tech_stack', 'relationship_type']),
            models.Index(fields=['to_tech_stack', 'relationship_type']),
        ]

    def __str__(self):
        return f"{self.from_tech_stack.name} -> {self.to_tech_stack.name} ({self.get_relationship_type_display()})"