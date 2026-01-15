"""
사용자 URL 설정
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # 인증
    #path('signup/', views.SignupView.as_view(), name='signup'),
    #path('login/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # 프로필
    path('me/', views.ProfileView.as_view(), name='profile'),

    # 구글 로그인 시작 (GET /auth/google)
    path('social/google/', views.GoogleLoginStartView.as_view(), name='google_start'),

    #  구글 콜백 처리 (POST /auth/google/callback)
    path('social/google/callback/', views.GoogleLoginView.as_view(), name='google_callback'),
]
