"""
사용자 뷰
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer# SignupSerializer, LoginSerializer
import requests
from decouple import config
from drf_yasg.utils import swagger_auto_schema # Swagger 설정을 위한 데코레이터 임포트
from drf_yasg import openapi # 상세한 파라미터 설정을 위한 모듈
import logging

""" class SignupView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer


class LoginView(APIView):
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
 """

class LogoutView(APIView):
    
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
            operation_summary="로그아웃",
            operation_description="사용자의 리프레시 토큰을 블랙리스트에 추가하여 로그아웃 처리합니다."
        )
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
    @swagger_auto_schema(
        operation_summary="구글 소셜 로그인 완료",
        operation_description="구글에서 받은 access_token을 이용해 JWT 토큰을 발급받습니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'access_token': openapi.Schema(type=openapi.TYPE_STRING, description='구글 access_token')
            },
            required=['access_token']
        ),
    )

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
            from .models import User    
            # 2. DB에서 사용자 조회/생성
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0], # 아이디 필드 채워주기
                    'name': name or 'Google User',
                    'is_deleted': False             # ERD에 따른 기본값
                }
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
class GoogleLoginStartView(APIView):
    """구글 로그인 시작 (Redirect URL 반환)"""
    
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        operation_summary="구글 로그인 시작",
        operation_description="구글 로그인 페이지로 리다이렉트할 수 있는 URL을 반환합니다.",
    ) 
    def get(self, request):
        # 환경변수에서 가져오기 (없으면 하드코딩된 값 사용)
        client_id = config('GOOGLE_OAUTH2_CLIENT_ID')
        redirect_uri = config('GOOGLE_REDIRECT_URI')
        
        # 구글 로그인 페이지 URL 생성
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=token"    # access_token을 바로 받기 위함
            "&scope=email%20profile"
        )
        
        return Response({"redirectUrl": google_auth_url})