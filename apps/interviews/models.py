"""
면접 준비 모델 정의
"""

from django.db import models
from django.conf import settings
from apps.trends.models import TechStack
from apps.jobs.models import JobPosting


class InterviewQuestion(models.Model):
    """
    면접 질문 모델
    """
    QUESTION_TYPE_CHOICES = [
        ('tech', '기술 질문'),
        ('experience', '경험 질문'),
        ('behavioral', '행동 질문'),
        ('situational', '상황 질문'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', '쉬움'),
        ('medium', '보통'),
        ('hard', '어려움'),
    ]

    tech_stack = models.ForeignKey(
        TechStack,
        on_delete=models.CASCADE,
        related_name='interview_questions',
        null=True,
        blank=True,
        verbose_name='기술 스택'
    )
    question = models.TextField(
        verbose_name='질문'
    )
    answer_guide = models.TextField(
        blank=True,
        null=True,
        verbose_name='답변 가이드'
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='tech',
        verbose_name='질문 유형'
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium',
        verbose_name='난이도'
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
        db_table = 'interview_question'
        verbose_name = '면접 질문'
        verbose_name_plural = '면접 질문 목록'

    def __str__(self):
        return self.question[:50]


class InterviewPractice(models.Model):
    """
    면접 연습 기록 모델
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interview_practices',
        verbose_name='사용자'
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interview_practices',
        verbose_name='채용 공고'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='연습 일자'
    )

    class Meta:
        db_table = 'interview_practice'
        verbose_name = '면접 연습'
        verbose_name_plural = '면접 연습 목록'


class InterviewAnswer(models.Model):
    """
    면접 답변 모델
    """
    practice = models.ForeignKey(
        InterviewPractice,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='면접 연습'
    )
    question = models.ForeignKey(
        InterviewQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='질문'
    )
    user_answer = models.TextField(
        verbose_name='사용자 답변'
    )
    ai_feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name='AI 피드백'
    )
    score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='점수'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )

    class Meta:
        db_table = 'interview_answer'
        verbose_name = '면접 답변'
        verbose_name_plural = '면접 답변 목록'
