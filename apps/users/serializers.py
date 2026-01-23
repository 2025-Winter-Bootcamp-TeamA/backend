"""
사용자 시리얼라이저
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
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

class SignupSerializer(serializers.ModelSerializer):
    """회원가입 시리얼라이저"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    username = serializers.CharField(required=True, max_length=128)

    class Meta:
        model = User
        fields = ['email', 'username', 'name', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': '비밀번호가 일치하지 않습니다.'
            })
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """로그인 시리얼라이저"""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            raise serializers.ValidationError('이메일과 비밀번호를 모두 입력해주세요.')
        
        try:
            # 커스텀 User 모델에서 email로 사용자 조회
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('이메일 또는 비밀번호가 올바르지 않습니다.')
        
        # 비밀번호 확인
        if not user.check_password(password):
            raise serializers.ValidationError('이메일 또는 비밀번호가 올바르지 않습니다.')
        
        # 계정 활성화 확인
        if not user.is_active:
            raise serializers.ValidationError('비활성화된 계정입니다.')
        
        # 삭제된 계정 확인
        if user.is_deleted:
            raise serializers.ValidationError('삭제된 계정입니다.')
        
        data['user'] = user
        return data