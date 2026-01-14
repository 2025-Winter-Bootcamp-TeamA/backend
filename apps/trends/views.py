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
    permission_classes = [AllowAny]
    serializer_class = TechStackByCategorySerializer

    def get_queryset(self):
        return TechStack.objects.filter(
            category_relations__category_id=self.kwargs['category_id'],
            is_deleted=False
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['category_id'] = self.kwargs.get('category_id')
        return context

    def list(self, request, *args, **kwargs):
        # Check for category existence before proceeding
        get_object_or_404(Category, pk=self.kwargs['category_id'], is_deleted=False)
        return super().list(request, *args, **kwargs)


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
