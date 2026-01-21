"""
TeamA API URL 설정
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from apps.users import views as user_views

# Swagger 문서 설정
schema_view = get_schema_view(
    openapi.Info(
        title="TeamA API",
        default_version='v1',
        description="개발 트렌드 분석 및 취업 지원 플랫폼 API",
        terms_of_service="https://www.teamA.com/terms/",
        contact=openapi.Contact(email="support@teamA.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # 관리자
    path('admin/', admin.site.urls),

    # API 엔드포인트
    #path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/trends/', include('apps.trends.urls')),
    path('api/v1/jobs/', include('apps.jobs.urls')),
    path('api/v1/resumes/', include('apps.resumes.urls')),
    path('api/v1/interviews/', include('apps.interviews.urls')),
    
    # 인증 (백엔드 OAuth Flow)
    #path('api/v1/auth/google/start/', user_views.GoogleLoginStartView.as_view(), name='google_start'),
    #path('api/v1/auth/google/callback/', user_views.GoogleLoginCallbackView.as_view(), name='google_callback'),

    # API 문서
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug Toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
