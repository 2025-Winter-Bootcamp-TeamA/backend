"""
채용 공고 및 기업 관련 API 뷰
"""

""" from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Corp, JobPosting, CorpBookmark
from .serializers import (
    CorpSerializer, CorpDetailSerializer,
    JobPostingSerializer, JobPostingDetailSerializer,
    CorpBookmarkSerializer
)
 """

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import filters # 추가

from .models import Corp, JobPosting, CorpBookmark
from .serializers import (
    CorpSerializer, CorpDetailSerializer,
    JobPostingSerializer, JobPostingDetailSerializer,
    CorpBookmarkListSerializer,CorpBookmarkCreateSerializer, 
    CorpBookmarkCreateResponseSerializer
)
class CorpListView(generics.ListAPIView):
    # [설정] 명세서의 '상태'가 '시작 전'이 아닌 '개발 중/완료'로 바뀌게 하는 설정들
    permission_classes = [AllowAny]
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpSerializer
    filter_backends = []
    
    @swagger_auto_schema(
        # 1. API 명세서의 'API Operation' 및 '텍스트' 칸 반영
        operation_summary="기업 검색 (목록 조회)",
        operation_description="기업 이름(corp_name)을 필터링하여 검색합니다. 2글자 미만은 400, 결과 없음은 404를 반환합니다.",
        
        # 3. 명세서의 'request body' 칸 반영 (GET이므로 Query Parameter로 표시)
        manual_parameters=[
            openapi.Parameter(
                'corp_name', openapi.IN_QUERY, 
                description="검색할 기업 이름", 
                type=openapi.TYPE_STRING
            )
        ],
        # 4. 명세서의 'response body' 칸 반영 (각 상태코드별 응답 형태)
        responses={
            200: CorpSerializer(many=True),
            400: openapi.Response(
                description="잘못된 요청 (2글자 미만)",
                examples={"application/json": {"error_code": "INVALID_PARAMETER", "message": "최소 2글자 이상 입력해주세요."}}
            ),
            404: openapi.Response(
                description="데이터 없음",
                examples={"application/json": {"message": "해당 이름의 기업을 찾을 수 없습니다."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        # [로직 1] 명세서 파라미터 가져오기 (이미지의 Parameters 탭 반영)
        corp_name = request.query_params.get('corp_name') # 'name' 대신 'corp_name' 권장
        
        # [로직 2] 명세서의 400 에러 조건 처리
        if corp_name and len(corp_name) < 2:
            return Response(
                {"error_code": "INVALID_PARAMETER", "message": "최소 2글자 이상 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if  corp_name:
            self.queryset = self.queryset.filter(name__icontains=corp_name)
        # [로직 3] 실제 DB에서 목록 조회 수행
        response = super().get(request, *args, **kwargs)

        # [로직 4] 명세서의 404 에러 조건 처리 (검색 결과가 0건일 때)
        if corp_name and not response.data:
            return Response(
                {"message": "해당 이름의 기업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        return response

class CorpDetailView(generics.RetrieveAPIView):
    """
    기업 상세 조회 View
    """
    permission_classes = [AllowAny]
    # 삭제되지 않은 기업들 중에서 찾습니다.
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpDetailSerializer

    @swagger_auto_schema(
        operation_summary="기업 상세 조회",
        operation_description="기업의 고유 ID(pk)를 사용하여 해당 기업의 상세 정보를 조회합니다.",
        responses={
            200: CorpDetailSerializer(),
            404: openapi.Response(
                description="데이터 없음",
                examples={"application/json": {"message": "해당 ID의 기업을 찾을 수 없습니다."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        # 1. 부모 클래스의 retrieve 로직을 실행하여 데이터를 가져옵니다.
        # 내부적으로 urls.py에서 넘겨받은 pk 값을 사용해 DB를 뒤집니다.
        try:
            return super().get(request, *args, **kwargs)
        except:
            # 2. 존재하지 않는 ID로 조회했을 경우 명세서 요구사항에 맞춰 404 에러를 반환합니다.
            return Response(
                {"message": "해당 ID의 기업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
    
class JobPostingListView(generics.ListAPIView):
    """채용 공고 목록"""
    permission_classes = [AllowAny]
    # 삭제되지 않은 채용공고 중에서 찾습니다.
    queryset = JobPosting.objects.filter(is_deleted=False)    
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        # 2. URL 경로에서 corp_id를 가져와서 해당 기업의 공고만 필터링합니다.
        corp_id = self.kwargs.get('corp_id')
        
        # 기업이 존재하는지 먼저 확인 (is_deleted=False 포함)
        if not Corp.objects.filter(id=corp_id, is_deleted=False).exists():
            return JobPosting.objects.none() # 빈 쿼리셋 반환
            
        return self.queryset.filter(corp_id=corp_id)
    
    @swagger_auto_schema(
        operation_summary="채용 공고 조회",
        operation_description="기업 ID를 기반으로 해당 기업이 올린 모든 채용 공고를 조회합니다.",
        responses={
            200: JobPostingSerializer(),
            404: openapi.Response(
                description="기업 없음",
                examples={"application/json": {"message": "해당 ID의 기업을 찾을 수 없습니다."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        # 3. 기업 존재 여부 체크 후 404 처리
        corp_id = self.kwargs.get('corp_id')
        if not Corp.objects.filter(id=corp_id, is_deleted=False).exists():
            return Response(
                {"message": "해당 ID의 기업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
        return super().get(request, *args, **kwargs)

class JobPostingDetailView(generics.RetrieveAPIView):
    """채용 공고 상세"""
    permission_classes = [AllowAny]
    queryset = JobPosting.objects.filter(is_deleted=False)
    serializer_class = JobPostingDetailSerializer


class JobPostingByTechView(generics.ListAPIView):
    """기술 스택별 채용 공고"""
    permission_classes = [AllowAny]
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        tech_stack_id = self.kwargs['tech_stack_id']
        return JobPosting.objects.filter(
            is_deleted=False,
            tech_stacks__tech_stack_id=tech_stack_id,
            tech_stacks__is_deleted=False
        ).distinct()

class CorpBookmarkListView(generics.ListCreateAPIView):
    """
    즐겨찾기 기업 목록 조회 및 추가
    """
    permission_classes = [IsAuthenticated]
    
    # [수정] 조회 시에는 List용, 생성 시에는 Create용 시리얼라이저를 사용하도록 분기 가능
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CorpBookmarkCreateSerializer
        return CorpBookmarkListSerializer

    def get_queryset(self):
        return CorpBookmark.objects.filter(
            user=self.request.user, 
            is_deleted=False
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="즐겨찾기 기업 추가",
        operation_description="기업 ID를 받아 본인의 즐겨찾기 목록에 추가합니다.",
        # [수정] 생성 응답 전용 시리얼라이저를 responses에 반영
        responses={201: CorpBookmarkCreateResponseSerializer()}
    )
    def post(self, request, *args, **kwargs):
        # 1. 시리얼라이저 초기화 (context 전달 필수)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. perform_create 로직을 직접 실행하여 저장된 객체(instance)를 받아옵니다.
        instance = serializer.save(user=self.request.user)
        
        # 3. 객체(instance)에서 직접 ID 값들을 꺼내서 응답합니다.
        return Response({
            'corp_bookmark_id': instance.id,
            'corp_id': instance.corp.id,
            'message': "기업이 즐겨찾기에 추가되었습니다."
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="즐겨찾기 기업 조회",
        operation_description="현재 로그인한 사용자가 추가한 즐겨찾기 목록을 조회합니다.",
        responses={200: CorpBookmarkListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class CorpBookmarkDetailView(generics.DestroyAPIView):
    """
    즐겨찾기 기업 삭제 
    """
    permission_classes = [IsAuthenticated]
    # 1. 삭제되지 않은 북마크 전체를 기본 대상으로 설정
    queryset = CorpBookmark.objects.filter(is_deleted=False)
    lookup_field = 'id'
    lookup_url_kwarg = 'corp_bookmark_id'

    def get_queryset(self):
        # 2. 현재 로그인한 유저의 북마크만 조회/삭제가 가능하도록 제한합니다.
        return self.queryset.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="즐겨찾기 기업 삭제",
        operation_description="즐겨찾기 고유 ID를 사용하여 본인의 즐겨찾기 목록에서 삭제합니다.",
        responses={
            200: "{'message': '기업 즐겨찾기가 해제되었습니다.'}",
            404: "북마크를 찾을 수 없거나 권한이 없음"
        }
    )
    def delete(self, request, *args, **kwargs):
        # 3. 실제 데이터를 찾을 때 유저 검증이 포함된 get_object를 사용합니다.
        instance = self.get_object()
        
        # 4.실제 DB 삭제 
        instance.delete()
        return Response(
            {'message': '기업 즐겨찾기가 해제되었습니다.'}, 
            status=status.HTTP_200_OK
        ) 
    
class CorpBookmarkToggleView(APIView):
    """기업 즐겨찾기 토글"""
    permission_classes = [IsAuthenticated]

    def post(self, request, corp_id):
        bookmark, created = CorpBookmark.objects.get_or_create(
            user=request.user,
            corp_id=corp_id,
            defaults={'is_deleted': False}
        )

        if not created:
            bookmark.is_deleted = not bookmark.is_deleted
            bookmark.save()

        action = '추가' if not bookmark.is_deleted else '삭제'
        return Response({
            'message': f'기업 즐겨찾기가 {action}되었습니다.',
            'is_bookmarked': not bookmark.is_deleted
        })
