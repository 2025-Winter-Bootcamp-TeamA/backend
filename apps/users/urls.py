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
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # 프로필
    path('auth/me/', views.ProfileView.as_view(), name='profile'),

    # 구글 OAuth 인증 (Authorization Code Flow)
    path('auth/google/start/', views.GoogleLoginStartView.as_view(), name='google_start'),
    path('auth/google/callback/', views.GoogleLoginCallbackView.as_view(), name='google_callback'),
]
