"""
사용자 URL 설정
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # 인증 (일반 signup/login은 주석 처리, 구글 소셜 로그인만 사용)
    # path('signup/', views.SignupView.as_view(), name='signup'),
    # path('login/', views.LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/<int:users_id>/', views.UserDeleteView.as_view(), name='user_delete'),
    # 프로필
    path('auth/me/', views.ProfileView.as_view(), name='profile'),

    # Google OAuth 인증
    path('auth/google/start/', views.GoogleLoginStartView.as_view(), name='google_start'),
    path('auth/google/callback/', views.GoogleLoginCallbackView.as_view(), name='google_callback'),
    path('auth/exchange-code/', views.ExchangeCodeView.as_view(), name='exchange_code'),
]
