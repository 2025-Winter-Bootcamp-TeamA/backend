"""
사용자 시리얼라이저
"""

from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # ERD 규격에 맞춰 응답하고 싶은 필드들을 리스트에 추가
        fields = [
            'id', 
            'username',  # 추가된 아이디 필드
            'email', 
            'name', 
            'profile_image', #추가된 이미지 
            'is_deleted', # 추가된 삭제 여부 필드
            'created_at', 
            'updated_at'
        ]
        # 읽기 전용 필드 설정 (생성/수정 시 자동 처리되는 필드들)
        read_only_fields = ['id', 'created_at', 'updated_at']

# ========== 일반 회원가입/로그인 시리얼라이저 (주석 처리, 구글 소셜 로그인만 사용) ==========
# class SignupSerializer(serializers.ModelSerializer):
#     """회원가입 시리얼라이저"""
#     password = serializers.CharField(write_only=True, min_length=8)
#     password_confirm = serializers.CharField(write_only=True)
#     username = serializers.CharField(required=True, max_length=128)
#     class Meta:
#         model = User
#         fields = ['email', 'username', 'name', 'password', 'password_confirm']
#     def validate(self, data): ...
#     def create(self, validated_data): ...
#
# class LoginSerializer(serializers.Serializer):
#     """로그인 시리얼라이저"""
#     email = serializers.EmailField()
#     password = serializers.CharField()
#     def validate(self, data): ...