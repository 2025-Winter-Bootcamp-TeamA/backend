"""
채용 공고 모델 정의
ERD의 corp, job_posting, job_posting_stack 테이블 기반
"""

from django.db import models
from django.conf import settings
from apps.trends.models import TechStack


class Corp(models.Model):
    """
    기업 모델
    ERD: corp 테이블
    """
    name = models.CharField(
        max_length=255,
        verbose_name='기업명'
    )
    logo_url = models.TextField(
        blank=True,
        null=True,
        verbose_name='로고 URL'
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='기업 주소'
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='위도'
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='경도'
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
        db_table = 'corp'
        verbose_name = '기업'
        verbose_name_plural = '기업 목록'

    def __str__(self):
        return self.name


class JobPosting(models.Model):
    """
    채용 공고 모델
    ERD: job_posting 테이블
    """
    corp = models.ForeignKey(
        Corp,
        on_delete=models.CASCADE,
        related_name='job_postings',
        verbose_name='기업'
    )
    url = models.TextField(
        verbose_name='채용 공고 URL'
    )
    title = models.TextField(
        blank=True,
        null=True,
        verbose_name='채용 공고 제목'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='직무 설명'
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='마감일'
    )
    career = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='경력'
    )
    stack_count = models.BigIntegerField(
        default=0,
        verbose_name='채용 공고 스택 수'
    )
    posting_number = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name='채용 공고 번호'
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
        db_table = 'job_posting'
        verbose_name = '채용 공고'
        verbose_name_plural = '채용 공고 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.corp.name} - {self.title or '채용 공고'}"


class JobPostingStack(models.Model):
    """
    채용 공고-기술 연결 모델
    ERD: job_posting_stack 테이블
    """
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='tech_stacks',
        verbose_name='채용 공고'
    )
    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='job_postings',
        verbose_name='기술 스택'
    )
    job_stack_count = models.BigIntegerField(
        default=0,
        verbose_name='채용공고 스택 언급량'
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
        db_table = 'job_posting_stack'
        verbose_name = '채용 공고-기술 연결'
        verbose_name_plural = '채용 공고-기술 연결 목록'


class CorpBookmark(models.Model):
    """
    기업 즐겨찾기 모델
    ERD: corp_bookmark 테이블
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corp_bookmarks',
        verbose_name='사용자'
    )
    corp = models.ForeignKey(
        Corp,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name='기업'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )

    class Meta:
        db_table = 'corp_bookmark'
        verbose_name = '기업 즐겨찾기'
        verbose_name_plural = '기업 즐겨찾기 목록'
        unique_together = ['user', 'corp']
