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
from .serializers import (
    TechStackSerializer, CategorySerializer,
    TechTrendSerializer, TechBookmarkSerializer, TechStackByCategorySerializer
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


class TechBookmarkListView(generics.ListAPIView):
    """내 기술 즐겨찾기 목록"""
    permission_classes = [IsAuthenticated]
    serializer_class = TechBookmarkSerializer

    def get_queryset(self):
        return TechBookmark.objects.filter(
            user=self.request.user,
            is_deleted=False
        )


class TechBookmarkToggleView(APIView):
    """기술 즐겨찾기 토글"""
    permission_classes = [IsAuthenticated]

    def post(self, request, tech_stack_id):
        bookmark, created = TechBookmark.objects.get_or_create(
            user=request.user,
            tech_stack_id=tech_stack_id,
            defaults={'is_deleted': False}
        )

        if not created:
            bookmark.is_deleted = not bookmark.is_deleted
            bookmark.save()

        action = '추가' if not bookmark.is_deleted else '삭제'
        return Response({
            'message': f'즐겨찾기가 {action}되었습니다.',
            'is_bookmarked': not bookmark.is_deleted
        })
