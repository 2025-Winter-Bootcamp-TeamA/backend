"""
트렌드 뷰
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import TechStack, Category, TechTrend, TechBookmark
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    TechStackSerializer, CategorySerializer,
    TechTrendSerializer, TechStackByCategorySerializer,
    TechBookmarkListSerializer, TechBookmarkCreateSerializer,
    TechBookmarkCreateResponseSerializer
)


class CategoryTechStackListView(generics.ListAPIView):
    """카테고리별 기술 스택 목록"""
    permission_classes = [AllowAny] # 모든 사용자 접근 허용
    serializer_class = TechStackByCategorySerializer # 시리얼라이저 지정

    def get_queryset(self): # API가 반환할 쿼리셋 정의
        return TechStack.objects.filter(
            category_relations__category_id=self.kwargs['category_id'],
            is_deleted=False
        ) # URL에서 받은 category_id에 속하는 기술과 삭제되지 않은 기술 스택 필터링

    def get_serializer_context(self): # 시리얼라이저 컨텍스트 오버라이드
        context = super().get_serializer_context() # 기본 컨텍스트 가져오기
        context['category_id'] = self.kwargs.get('category_id') # context에 category_id 추가
        return context

    # list 메서드 오버라이드
    def list(self, request, *args, **kwargs): 
        get_object_or_404(Category, pk=self.kwargs['category_id'], is_deleted=False) #url에서 받은 category_id 값을 가져옴, kwargs는 딕셔너리 형태
        # 유효성 검사 후 리스트 반환(삭제되었거나, 존재하지 않으면 404 에러 발생)
        return super().list(request, *args, **kwargs) # get_queryset 메소드로 얻은 쿼리셋을 직렬화 하여 HTTP 응답 


class TechStackListView(generics.ListAPIView):
    """기술 스택 목록"""
    permission_classes = [AllowAny]
    queryset = TechStack.objects.filter(is_deleted=False)
    serializer_class = TechStackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']


class TechStackDetailView(generics.RetrieveAPIView):
    """기술 스택 상세"""
    permission_classes = [AllowAny]
    queryset = TechStack.objects.filter(is_deleted=False)
    serializer_class = TechStackSerializer


class TechDocsURLView(APIView):
    """기술 스택 공식 문서 URL 조회"""
    permission_classes = [AllowAny]

    def get(self, request, tech_stack_id):
        # is_deleted=False 조건으로 삭제되지 않은 객체만 조회, 없으면 404 에러
        tech_stack = get_object_or_404(TechStack, pk=tech_stack_id, is_deleted=False)

        return Response({'docs_url': tech_stack.docs_url})


class CategoryListView(generics.ListAPIView):
    """카테고리 목록"""
    permission_classes = [AllowAny]
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer


class TechTrendListView(generics.ListAPIView):
    """기술 트렌드 목록"""
    permission_classes = [AllowAny]
    queryset = TechTrend.objects.filter(is_deleted=False)
    serializer_class = TechTrendSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tech_stack', 'reference_date']


class TrendRankingView(APIView):
    """트렌드 랭킹 조회"""
    permission_classes = [AllowAny]

    def get(self, request):
        # 최근 트렌드 기준 상위 10개
        trends = TechTrend.objects.filter(
            is_deleted=False
        ).order_by('-reference_date', '-mention_count')[:10]

        serializer = TechTrendSerializer(trends, many=True)
        return Response(serializer.data)


class TechBookmarkListCreateAPIView(APIView):
    """
    기술 즐겨찾기 목록 조회 및 생성 API
    - GET /tech-bookmarks: 즐겨찾기 기술 목록 조회
    - POST /tech-bookmarks: 즐겨찾기 기술 추가
    """
    #permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]  # 인증 없이도 접근 가능하도록 변경(테스트 목적)


    def get(self, request):
        bookmarks = TechBookmark.objects.filter(user=request.user).order_by('-created_at')
        serializer = TechBookmarkListSerializer(bookmarks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=TechBookmarkCreateSerializer)
    def post(self, request):
        serializer = TechBookmarkCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        tech_id = serializer.validated_data.get('tech_id')
        tech_stack = get_object_or_404(TechStack, id=tech_id)
        
        tech_bookmark = TechBookmark.objects.create(user=request.user, tech_stack=tech_stack)

        response_serializer = TechBookmarkCreateResponseSerializer({
            'tech_bookmark_id': tech_bookmark.id,
            'tech_stack_id': tech_bookmark.tech_stack.id,
            'message': "즐겨찾기에 추가되었습니다."
        })
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TechBookmarkDeleteAPIView(APIView):
    """
    기술 즐겨찾기 삭제 API
    - DELETE /tech-bookmarks/{tech_bookmark_id}: 즐겨찾기 기술 삭제
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, tech_bookmark_id):
        bookmark = get_object_or_404(TechBookmark, id=tech_bookmark_id, user=request.user)
        bookmark.delete()
        return Response({'message': '즐겨찾기가 해제 되었습니다.'}, status=status.HTTP_200_OK)