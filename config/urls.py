from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

def api_v1_root(request):
    """API v1 루트: 서버 동작 확인 및 엔드포인트 안내."""
    return JsonResponse({
        "message": "TeamA API v1",
        "endpoints": {
            "users": "/api/v1/users/",
            "trends": "/api/v1/trends/",
            "jobs": "/api/v1/jobs/",
            "resumes": "/api/v1/resumes/",
            "interviews": "/api/v1/interviews/",
            "metrics": "/metrics", # 추가됨
            "swagger": "/swagger/",
            "redoc": "/redoc/",
        },
    })

schema_view = get_schema_view(
    openapi.Info(
        title="TeamA API",
        default_version='v1',
        description="개발 트렌드 분석 및 취업 지원 플랫폼 API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # 관리자
    path('admin/', admin.site.urls),

    # API v1 루트
    path('api/v1/', api_v1_root),

    # API 엔드포인트
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/trends/', include('apps.trends.urls')),
    path('api/v1/jobs/', include('apps.jobs.urls')),
    path('api/v1/resumes/', include('apps.resumes.urls')),
    path('api/v1/interviews/', include('apps.interviews.urls')),
    
    # Prometheus 지표 엔드포인트
    path('', include('django_prometheus.urls')), # 추가: /metrics 경로 활성화

    # API 문서
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]