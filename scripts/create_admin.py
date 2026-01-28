"""
관리자 계정 생성 스크립트
로컬 및 프로덕션 환경 모두 지원
"""
import os
import sys
import django

# Django 설정 로드
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 환경변수에서 DJANGO_SETTINGS_MODULE 확인, 없으면 local 사용
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
django.setup()

from apps.users.models import User
from django.conf import settings


def create_admin():
    """관리자 계정 생성"""
    # 환경별 기본 계정 정보
    if settings.DEBUG:
        # 로컬 환경
        email = "admin@teamA.com"
        username = "admin"
        name = "관리자"
        password = "admin1234"
    else:
        # 프로덕션 환경
        email = "admin@devroad.cloud"
        username = "admin"
        name = "DevRoad Admin"
        password = "TeamA2025!"

    # 기존 사용자 확인
    if User.objects.filter(email=email).exists():
        print(f"❌ {email} 이미 존재합니다.")
        print("\n기존 superuser 목록:")
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            print(f"  - {user.email} (ID: {user.id}, Active: {user.is_active})")

        # 비밀번호 재설정 옵션
        reset = input(f"\n{email}의 비밀번호를 재설정하시겠습니까? (y/n): ")
        if reset.lower() == 'y':
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.save()
            print(f"\n✅ 비밀번호가 재설정되었습니다!")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
        return

    # 새 superuser 생성
    user = User.objects.create_superuser(
        email=email,
        username=username,
        name=name,
        password=password
    )

    # 환경별 Admin URL
    if settings.DEBUG:
        admin_url = "http://localhost:8000/admin/"
    else:
        admin_url = "https://api.devroad.cloud/admin/"

    print("\n" + "="*60)
    print("✅ 관리자 계정이 생성되었습니다!")
    print("="*60)
    print(f"\n📧 Email: {email}")
    print(f"🔑 Password: {password}")
    print(f"\n🌐 Admin URL: {admin_url}")
    print(f"\n환경: {'로컬 개발' if settings.DEBUG else '프로덕션'}")
    print("\n" + "="*60)


if __name__ == '__main__':
    create_admin()
