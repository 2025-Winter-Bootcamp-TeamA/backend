"""
사용자 뷰
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
import requests
from decouple import config
from drf_yasg.utils import swagger_auto_schema # Swagger 설정을 위한 데코레이터 임포트
from drf_yasg import openapi # 상세한 파라미터 설정을 위한 모듈
import logging
from django.shortcuts import get_object_or_404, redirect
from django.core.cache import cache
from urllib.parse import quote
import secrets
from .models import User  
# ========== 일반 로그인/회원가입 (주석 처리, 구글 소셜 로그인만 사용) ==========
# class SignupView(generics.CreateAPIView):
#     """일반 회원가입"""
#     permission_classes = [AllowAny]
#     serializer_class = SignupSerializer
#     @swagger_auto_schema(...)
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)
#
# class LoginView(APIView):
#     """일반 JWT 로그인"""
#     permission_classes = [AllowAny]
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         ...
#         return Response({'refresh': ..., 'access': ..., 'user': ...})

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


# ========== Google OAuth 로그인 관련 코드 (주석 처리) ==========
# class GoogleLoginView(APIView):
#     """구글 소셜 로그인"""
#     permission_classes = [AllowAny]
#     @swagger_auto_schema(
#         #operation_summary="구글 소셜 로그인 완료",
#         operation_description="구글에서 받은 access_token을 이용해 JWT 토큰을 발급받습니다.",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'access_token': openapi.Schema(type=openapi.TYPE_STRING, description='구글 access_token')
#             },
#             required=['access_token']
#         ),
#     )

#     def post(self, request):
#         access_token = request.data.get('access_token')

#         if not access_token:
#             return Response(
#                 {'error': 'access_token이 필요합니다.'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             # 1. 구글 API로 사용자 정보 조회
#             response = requests.get(
#                 'https://www.googleapis.com/oauth2/v3/userinfo',
#                 headers={'Authorization': f'Bearer {access_token}'},
#                 timeout=10
#             )
#             response.raise_for_status()
#             user_data = response.json()

#             email = user_data.get('email')
#             name = user_data.get('name')

#             if not email:
#                 return Response(
#                     {'error': '구글에서 이메일을 가져올 수 없습니다.'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             from .models import User    
#             # 2. DB에서 사용자 조회/생성
#             user, created = User.objects.get_or_create(
#                 email=email,
#                 defaults={
#                     'username': email.split('@')[0], # 아이디 필드 채워주기
#                     'name': name or 'Google User',
#                     'is_deleted': False             # ERD에 따른 기본값
#                 }
#             )

#             if created:
#                 # 새 사용자 생성 시 이름 업데이트
#                 if name:
#                     user.name = name
#                     user.save()

#             # 3. JWT 토큰 발급
#             refresh = RefreshToken.for_user(user)

#             # 4. 응답 반환
#             return Response({
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token),
#                 'user': UserSerializer(user).data
#             })

#         except requests.RequestException as e:
#             logging.error(f'Google API call failed: {e}')
#             return Response(
#                 {'error': '구글 API 호출에 실패했습니다.'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         except Exception as e:
#             logging.exception('Unexpected error during Google login')
#             return Response(
#                 {'error': '로그인 처리 중 오류가 발생했습니다.'},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
class GoogleLoginStartView(APIView):
    """구글 로그인 시작 (Redirect URL 반환)"""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="구글 로그인 페이지로 리다이렉트할 수 있는 URL을 반환합니다.",
    )
    def get(self, request):
        client_id = config('GOOGLE_OAUTH2_CLIENT_ID')
        redirect_uri = config('GOOGLE_REDIRECT_URI')

        # CSRF 방지를 위한 state 생성 및 세션 저장
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state

        redirect_uri_encoded = quote(redirect_uri, safe='')

        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri_encoded}"
            "&response_type=code"
            "&scope=email%20profile%20openid"
            "&access_type=offline"
            f"&state={state}"
            "&prompt=consent"
        )

        return Response({"redirectUrl": google_auth_url})


class GoogleLoginCallbackView(APIView):
    """구글 로그인 콜백 처리 (Authorization Code → JWT)"""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Google에서 받은 authorization code를 access_token으로 교환하고 JWT를 발급합니다.",
        manual_parameters=[
            openapi.Parameter('code', openapi.IN_QUERY, description="Google authorization code", type=openapi.TYPE_STRING),
            openapi.Parameter('state', openapi.IN_QUERY, description="CSRF 방지 state", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response(
                {'error': 'authorization code가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # state 검증 (CSRF 방지)
        state = request.GET.get('state')
        session_state = request.session.pop('oauth_state', None)
        if not state or state != session_state:
            return Response(
                {'error': '유효하지 않은 state입니다. 다시 시도해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
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

            user_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            user_response.raise_for_status()
            user_data = user_response.json()

            email = user_data.get('email')
            name = user_data.get('name')
            picture = user_data.get('picture')

            if not email:
                return Response(
                    {'error': '구글에서 이메일을 가져올 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'name': name or 'Google User',
                    'profile_image': picture,
                    'is_deleted': False
                }
            )
            if not created:
                is_changed = False
                if name and user.name != name:
                    user.name = name
                    is_changed = True
                if picture and user.profile_image != picture:
                    user.profile_image = picture
                    is_changed = True
                if is_changed:
                    user.save()

            refresh = RefreshToken.for_user(user)
            frontend_url = config('FRONTEND_URL')
            # 일회용 코드로 토큰 전달 (URL 쿼리 노출 방지)
            one_time_code = secrets.token_urlsafe(32)
            cache.set(
                f'auth_code:{one_time_code}',
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'profile_image': picture or getattr(user, 'profile_image', None),
                },
                timeout=300,
            )
            redirect_url = f"{frontend_url}/auth/callback?code={one_time_code}"
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


class ExchangeCodeView(APIView):
    """
    OAuth 콜백 후 일회용 code를 JWT로 교환 (토큰 URL 노출 방지)
    POST /api/v1/users/auth/exchange-code/  body: { "code": "..." }
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="일회용 인증 코드를 JWT(access, refresh) 및 profile_image로 교환합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'code': openapi.Schema(type=openapi.TYPE_STRING, description='일회용 코드')},
            required=['code'],
        ),
        responses={200: 'access, refresh, profile_image(선택)', 400: '잘못된/만료된 코드'},
    )
    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'code가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cache_key = f'auth_code:{code}'
        data = cache.get(cache_key)
        if not data:
            return Response(
                {'error': '만료되었거나 잘못된 코드입니다. 다시 로그인해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cache.delete(cache_key)
        return Response({
            'access': data['access'],
            'refresh': data['refresh'],
            'profile_image': data.get('profile_image'),
        })


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