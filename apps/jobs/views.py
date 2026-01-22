# from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import filters

from .models import Corp, JobPosting, CorpBookmark
from .serializers import (
    CorpSerializer, CorpDetailSerializer,
    JobPostingSerializer, JobPostingDetailSerializer,
    CorpBookmarkListSerializer, CorpBookmarkCreateSerializer,
    CorpBookmarkCreateResponseSerializer
)

class CorpListView(generics.ListAPIView):
    """
    기업 목록 조회 및 검색 View
    """
    permission_classes = [AllowAny]
    # 논리적으로 삭제되지 않은 기업만 조회 대상으로 설정합니다.
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpSerializer
    filter_backends = []
    
    @swagger_auto_schema(
        operation_summary="기업 검색 (목록 조회)",
        operation_description="기업 이름(corp_name)을 필터링하여 부분 일치 검색을 수행합니다. 검색어가 없으면 전체 목록을 반환합니다.",
        manual_parameters=[
            openapi.Parameter(
                'corp_name', openapi.IN_QUERY, 
                description="검색할 기업 이름 (부분 일치)", 
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: CorpSerializer(many=True),
        }
    )
    def get(self, request, *args, **kwargs):
        # 쿼리 파라미터 추출
        corp_name = request.query_params.get('corp_name')

        # 검색 로직: 상위 클래스의 get 호출 전 필터링 적용
        # self.get_queryset()을 호출하여 인스턴스 변수가 아닌 메서드 체이닝으로 처리하는 것이 안전함
        queryset = self.get_queryset()
        if corp_name and corp_name.strip():
            # 부분 일치 검색 (대소문자 구분 없음)
            queryset = queryset.filter(name__icontains=corp_name.strip())
        
        # 필터링된 쿼리셋으로 시리얼라이징 수행
        serializer = self.get_serializer(queryset, many=True)
        
        # 검색 결과가 없어도 빈 배열 반환 (404 대신 200)
        return Response(serializer.data)


class CorpDetailView(generics.RetrieveAPIView):
    """
    기업 상세 조회 View
    """
    permission_classes = [AllowAny]
    # is_deleted=False 필터링을 통해 삭제된 기업 접근 시 자동으로 404가 발생하도록 유도
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpDetailSerializer

    @swagger_auto_schema(
        operation_summary="기업 상세 조회",
        operation_description="기업의 고유 ID(pk)를 사용하여 해당 기업의 상세 정보를 조회합니다.",
        responses={
            200: CorpDetailSerializer(),
            404: "해당 ID의 기업을 찾을 수 없습니다."
        }
    )
    def retrieve(self, request, *args, **kwargs):
        # DRF의 기본 retrieve는 get_object() 실패 시 Http404를 발생시킴
        # 이를 커스텀 메시지로 반환하기 위해 오버라이딩
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except (Http404, Corp.DoesNotExist):
            # Http404 예외 등을 포착하여 요구사항에 맞는 JSON 응답 반환
            # 주의: 실제 프로덕션에서는 Http404만 잡는 것이 좋으나, 
            # 사용자의 코드 의도(커스텀 메시지)를 반영하여 처리
            return Response(
                {"message": "해당 ID의 기업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )


class JobPostingListView(generics.ListAPIView):
    """
    특정 기업의 채용 공고 목록 조회 View
    """
    permission_classes = [AllowAny]
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        # URL 설정(urls.py)에서 정의한 변수명 'corp_id'를 가져와야 함 ('pk'가 아님)
        corp_id = self.kwargs.get('corp_id')
        
        # 해당 기업이 실제로 존재하는지(삭제되지 않았는지) 확인
        # get_object_or_404를 사용하지 않는 이유: 리스트 조회에서 상위 리소스가 없을 때 빈 리스트가 아닌 404를 명시적으로 주기 위함
        return JobPosting.objects.filter(
            corp_id=corp_id,
            corp__is_deleted=False, # 기업이 삭제된 경우 공고도 조회되지 않아야 함
            is_deleted=False
        )
    
    @swagger_auto_schema(
        operation_summary="채용 공고 조회",
        operation_description="기업 ID를 기반으로 해당 기업이 올린 모든 채용 공고를 조회합니다.",
        responses={
            200: JobPostingSerializer(many=True),
            404: "해당 ID의 기업을 찾을 수 없습니다."
        }
    )
    def list(self, request, *args, **kwargs):
        # urls.py의 변수명인 corp_id 사용
        corp_id = self.kwargs.get('corp_id')

        # 기업 존재 여부 검증 (DB 최적화: exists() 사용)
        if not Corp.objects.filter(id=corp_id, is_deleted=False).exists():
            return Response(
                {"message": "해당 ID의 기업을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return super().list(request, *args, **kwargs)


class JobPostingDetailView(generics.RetrieveAPIView):
    """채용 공고 상세 View"""
    permission_classes = [AllowAny]
    queryset = JobPosting.objects.filter(is_deleted=False)
    serializer_class = JobPostingDetailSerializer


class JobPostingByTechView(generics.ListAPIView):
    """기술 스택별 채용 공고 조회 View"""
    permission_classes = [AllowAny]
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        tech_stack_id = self.kwargs.get('tech_stack_id')
        return JobPosting.objects.filter(
            is_deleted=False,
            tech_stacks__tech_stack_id=tech_stack_id,
            tech_stacks__is_deleted=False
        ).distinct() # 중복 제거


class CorpBookmarkListView(generics.ListCreateAPIView):
    """
    즐겨찾기 기업 목록 조회 및 추가 View
    """
    permission_classes = [IsAuthenticated]
    
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
        responses={201: CorpBookmarkCreateResponseSerializer()}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(user=self.request.user)
        
        return Response({
            'corp_bookmark_id': instance.id,
            'corp_id': instance.corp.id,
            'message': "기업이 즐겨찾기에 추가되었습니다."
        }, status=status.HTTP_201_CREATED)


class CorpBookmarkDetailView(generics.DestroyAPIView):
    """
    즐겨찾기 기업 삭제 View
    """
    permission_classes = [IsAuthenticated]
    # 기본 쿼리셋 정의 (get_object에서 user 필터링 추가됨)
    queryset = CorpBookmark.objects.filter(is_deleted=False)
    lookup_field = 'id'
    lookup_url_kwarg = 'corp_bookmark_id'

    def get_queryset(self):
        # 본인의 북마크만 삭제 가능하도록 제한
        return self.queryset.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="즐겨찾기 기업 삭제",
        operation_description="즐겨찾기 고유 ID를 사용하여 본인의 즐겨찾기 목록에서 삭제합니다.",
        responses={
            200: "기업 즐겨찾기가 해제되었습니다.",
            404: "북마크를 찾을 수 없거나 권한이 없음"
        }
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete() # 실제 삭제 (Soft Delete 필요 시 instance.is_deleted=True 후 save)
        return Response(
            {'message': '기업 즐겨찾기가 해제되었습니다.'}, 
            status=status.HTTP_200_OK
        )