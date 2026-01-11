"""
이력서 뷰
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Resume
from .serializers import ResumeSerializer, ResumeDetailSerializer


class ResumeListCreateView(generics.ListCreateAPIView):
    """이력서 목록 조회 및 생성"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeSerializer

    def get_queryset(self):
        return Resume.objects.filter(
            user=self.request.user,
            is_deleted=False
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ResumeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """이력서 상세 조회/수정/삭제"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeDetailSerializer

    def get_queryset(self):
        return Resume.objects.filter(
            user=self.request.user,
            is_deleted=False
        )

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save()


class ResumeAnalyzeView(APIView):
    """이력서 분석 (AI 기반)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            resume = Resume.objects.get(
                pk=pk,
                user=request.user,
                is_deleted=False
            )
        except Resume.DoesNotExist:
            return Response(
                {'error': '이력서를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: AI 분석 로직 구현 (Celery 태스크로 처리)
        # 현재는 더미 응답 반환
        return Response({
            'resume_id': resume.id,
            'analysis': {
                'tech_stacks': ['Python', 'Django', 'React'],
                'strengths': ['백엔드 개발 경험'],
                'improvements': ['프로젝트 경험 추가 권장'],
            },
            'message': '이력서 분석이 완료되었습니다.'
        })


class ResumeMatchingView(APIView):
    """이력서-채용공고 매칭"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, job_posting_id):
        try:
            resume = Resume.objects.get(
                pk=pk,
                user=request.user,
                is_deleted=False
            )
        except Resume.DoesNotExist:
            return Response(
                {'error': '이력서를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: 매칭 로직 구현 (Celery 태스크로 처리)
        # 현재는 더미 응답 반환
        return Response({
            'resume_id': resume.id,
            'job_posting_id': job_posting_id,
            'matching_result': {
                'matching_rate': 75.5,
                'matched_skills': ['Python', 'Django'],
                'missing_skills': ['AWS', 'Docker'],
                'feedback': '클라우드 경험을 추가하면 매칭률이 높아질 것입니다.'
            }
        })
