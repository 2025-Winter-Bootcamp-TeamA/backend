"""
사용자 모델 정의
ERD의 user 테이블 기반
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """사용자 매니저 클래스"""

    def create_user(self, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """관리자 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    사용자 모델
    ERD: user 테이블
    """
    email = models.EmailField(
        max_length=128,
        unique=True,
        verbose_name='이메일'
    )
    name = models.CharField(
        max_length=128,
        verbose_name='이름'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화 여부'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='스태프 여부'
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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'user'
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'

    def __str__(self):
        return self.email
