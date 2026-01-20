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
from django.shortcuts import get_object_or_404
from .models import User  
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
            #operation_summary="로그아웃",
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
        #operation_summary="구글 소셜 로그인 완료",
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
        #operation_summary="구글 로그인 시작",
        operation_description="구글 로그인 페이지로 리다이렉트할 수 있는 URL을 반환합니다.",
    ) 
    def get(self, request):
        # 환경변수에서 가져오기
        client_id = config('GOOGLE_OAUTH2_CLIENT_ID')
        redirect_uri = config('GOOGLE_REDIRECT_URI')
        
        # 구글 로그인 페이지 URL 생성
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            "&response_type=code"          # code를 받기 위함 (Authorization Code Flow)
            "&scope=email%20profile%20openid"
            "&access_type=offline"         # refresh_token도 받기
        )
        
        return Response({"redirectUrl": google_auth_url})


class GoogleLoginCallbackView(APIView):
    """구글 로그인 콜백 처리 (Authorization Code → JWT)"""
    
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        #operation_summary="구글 로그인 콜백",
        operation_description="Google에서 받은 authorization code를 access_token으로 교환하고 JWT를 발급합니다.",
        manual_parameters=[
            openapi.Parameter('code', openapi.IN_QUERY, description="Google authorization code", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        """GET 요청으로 code를 받아서 처리"""
        code = request.GET.get('code')
        
        if not code:
            return Response(
                {'error': 'authorization code가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. code를 access_token으로 교환
            client_id = config('GOOGLE_OAUTH2_CLIENT_ID')
            client_secret = config('GOOGLE_OAUTH2_CLIENT_SECRET')
            redirect_uri = config('GOOGLE_REDIRECT_URI')
            
            token_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'code': code,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                },
                timeout=10
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return Response(
                    {'error': 'access_token을 가져올 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 2. access_token으로 사용자 정보 조회
            user_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            user_response.raise_for_status()
            user_data = user_response.json()
            
            email = user_data.get('email')
            name = user_data.get('name')
            
            if not email:
                return Response(
                    {'error': '구글에서 이메일을 가져올 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .models import User
            
            # 3. DB에서 사용자 조회/생성
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'name': name or 'Google User',
                    'is_deleted': False
                }
            )
            
            if created and name:
                user.name = name
                user.save()
            
            # 4. JWT 토큰 발급
            refresh = RefreshToken.for_user(user)
            
            # 5. 프론트엔드로 리다이렉트 (토큰을 쿼리 파라미터로 전달)
            frontend_url = config('FRONTEND_URL')
            redirect_url = (
                f"{frontend_url}/auth/callback"
                f"?access={str(refresh.access_token)}"
                f"&refresh={str(refresh)}"
            )
            
            from django.shortcuts import redirect
            return redirect(redirect_url)
            
        except requests.RequestException as e:
            logging.error(f'Google API call failed: {e}')
            return Response(
                {'error': 'Google API 호출에 실패했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logging.exception('Unexpected error during Google login callback')
            return Response(
                {'error': '로그인 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class UserDeleteView(APIView):
    """
    회원 삭제 (논리 삭제: is_deleted=True, is_active=False)
    API: DELETE /auth/{users_id}
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="특정 사용자의 계정을 비활성화(Soft Delete) 합니다.",
        responses={
            204: "삭제 성공",
            403: "권한 없음 (본인 계정만 삭제 가능)",
            404: "사용자를 찾을 수 없음"
        }
    )
    def delete(self, request, users_id):
        # 1. 삭제할 대상 객체 조회
        target_user = get_object_or_404(User, id=users_id)

        # 2. 권한 검증: 본인이거나 관리자(is_staff)인 경우에만 삭제 허용
        if request.user.id != target_user.id and not request.user.is_staff:
            return Response(
                {'error': '본인의 계정만 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # 3. 논리 삭제 처리 (DB에서 지우지 않고 플래그만 변경)
            target_user.is_deleted = True
            target_user.is_active = False  # 로그인 차단
            target_user.save()

            return Response(
                {'message': f'회원(ID: {users_id}) 탈퇴 처리가 완료되었습니다.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            # 에러 로그 출력 등 필요 시 추가
            return Response(
                {'error': '회원 삭제 중 오류가 발생했습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )