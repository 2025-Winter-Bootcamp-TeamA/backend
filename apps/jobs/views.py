"""
채용 공고 뷰
"""

from rest_framework import generics, status
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


class CorpListView(generics.ListAPIView):
    """기업 목록"""
    permission_classes = [AllowAny]
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']


class CorpDetailView(generics.RetrieveAPIView):
    """기업 상세"""
    permission_classes = [AllowAny]
    queryset = Corp.objects.filter(is_deleted=False)
    serializer_class = CorpDetailSerializer


class JobPostingListView(generics.ListAPIView):
    """채용 공고 목록"""
    permission_classes = [AllowAny]
    queryset = JobPosting.objects.filter(is_deleted=False)
    serializer_class = JobPostingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['corp']


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


class CorpBookmarkListView(generics.ListAPIView):
    """내 기업 즐겨찾기 목록"""
    permission_classes = [IsAuthenticated]
    serializer_class = CorpBookmarkSerializer

    def get_queryset(self):
        return CorpBookmark.objects.filter(
            user=self.request.user,
            is_deleted=False
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
