from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    """사용자 매니저 클래스"""

    def create_user(self, email, username, name, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다.')
        if not username:
            raise ValueError('아이디는 필수입니다.')
            
        email = self.normalize_email(email)
        user = self.model(
            email=email, 
            username=username, 
            name=name, 
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, name, password=None, **extra_fields):
        """관리자 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    사용자 모델 (ERD: 회원 테이블 규격 준수)
    """
    # 1. 회원 ID (BIGSERIAL 대응)
    id = models.BigAutoField(primary_key=True)

    # 2. 아이디 (VARCHAR 128) - ERD의 '아이디' 필드
    username = models.CharField(
        max_length=128,
        unique=True,
        verbose_name='아이디'
    )

    # 3. 이메일 (VARCHAR 128)
    email = models.EmailField(
        max_length=128,
        unique=True,
        verbose_name='이메일'
    )

    # 4. 이름 (VARCHAR 128) - 필수 정보
    name = models.CharField(
        max_length=128,
        verbose_name='이름'
    )

    # 5. 삭제여부 (BOOLEAN)
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='삭제 여부'
    )

    # 6. 등록일자 및 수정일자 (TIMESTAMP)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일자'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일자'
    )

    # Django 관리용 필드
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    # 로그인 시 사용할 필드 (이메일로 로그인할지, 아이디로 로그인할지 선택)
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username', 'name']

    profile_image = models.URLField(
        max_length=500, 
        blank=True, 
        null=True, 
        verbose_name='프로필 이미지'
    )
    class Meta:
        db_table = 'user'
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'

    def __str__(self):
        return f"{self.email} ({self.name})"