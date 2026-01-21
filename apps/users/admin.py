"""
사용자 관리자 설정
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from django.utils.html import mark_safe  

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # 리스트 화면 설정
    list_display = ['email', 'name', 'profile_image_preview', 'is_active', 'is_staff', 'created_at']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'name']
    ordering = ['-created_at']

    # 상세(수정) 화면 설정
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('개인정보', {
            'fields': ('name', 'profile_image', 'profile_image_preview') # 여기에 추가
        }),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('날짜', {'fields': ('created_at', 'updated_at')}),
    )
    
    # 읽기 전용 필드 설정 (이미지 미리보기는 수정 불가능하므로 여기 등록)
    readonly_fields = ['created_at', 'updated_at', 'profile_image_preview']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'profile_image'),
        }),
    )

    # 이미지 미리보기 메서드 구현
    def profile_image_preview(self, obj):
        if obj.profile_image:
            # 보안을 위해 mark_safe를 사용하여 HTML <img> 태그를 렌더링
            return mark_safe(f'<img src="{obj.profile_image}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />')
        return "이미지 없음"
    
    # 어드민 컬럼 이름 설정
    profile_image_preview.short_description = "프로필 이미지"