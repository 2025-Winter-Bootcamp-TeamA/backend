from django.db import models
from django.conf import settings
from apps.trends.models import TechStack
from apps.jobs.models import JobPosting

class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes', verbose_name='사용자')
    title = models.CharField(max_length=128, verbose_name='이력서 제목')
    url = models.TextField(blank=True, null=True, verbose_name='이력서 URL')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일자')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일자')
    is_deleted = models.BooleanField(default=False, verbose_name='삭제 여부')

    class Meta:
        db_table = 'resume'
        verbose_name = '이력서'
        verbose_name_plural = '이력서 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class ResumeStack(models.Model):
    """이력서에서 추출된 기술 스택 저장 모델"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='tech_stacks', verbose_name='이력서')
    tech_stack = models.ForeignKey(TechStack, on_delete=models.CASCADE, related_name='resumes', verbose_name='기술 스택')

    class Meta:
        db_table = 'resume_stack'
        verbose_name = '이력서-기술 연결'
        verbose_name_plural = '이력서-기술 연결 목록'


class ResumeMatching(models.Model):
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='resume_matchings', verbose_name='채용 공고')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='job_matchings', verbose_name='이력서')
    score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='매칭률')
    feedback = models.TextField(blank=True, null=True, verbose_name='분석 내용')
    question = models.TextField(blank=True, null=True, verbose_name='면접 질문')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일자')
    is_deleted = models.BooleanField(default=False, verbose_name='삭제 여부')

    class Meta:
        db_table = 'resume_matching'
        verbose_name = '이력서 매칭'
        verbose_name_plural = '이력서 매칭 목록'