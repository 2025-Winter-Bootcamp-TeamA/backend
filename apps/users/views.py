"""
사용자 뷰
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, SignupSerializer, LoginSerializer
import requests
from decouple import config


class SignupView(generics.CreateAPIView):
    """회원가입"""
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer


class LoginView(APIView):
    """로그인"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    """로그아웃"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': '로그아웃 되었습니다.'})
        except Exception:
            return Response(
                {'error': '로그아웃 실패'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """사용자 프로필 조회/수정"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class GoogleLoginView(APIView):
    """구글 소셜 로그인"""
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.data.get('access_token')

        if not access_token:
            return Response(
                {'error': 'access_token이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. 구글 API로 사용자 정보 조회
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            response.raise_for_status()
            user_data = response.json()

            email = user_data.get('email')
            name = user_data.get('name')

            if not email:
                return Response(
                    {'error': '구글에서 이메일을 가져올 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. DB에서 사용자 조회/생성
            from .models import User
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'name': name or ''}
            )

            if created:
                # 새 사용자 생성 시 이름 업데이트
                if name:
                    user.name = name
                    user.save()

            # 3. JWT 토큰 발급
            refresh = RefreshToken.for_user(user)

            # 4. 응답 반환
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
            import logging

        except requests.RequestException as e:
            logging.error(f'Google API call failed: {e}')
            return Response(
                {'error': '구글 API 호출에 실패했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logging.exception('Unexpected error during Google login')
            return Response(
                {'error': '로그인 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )