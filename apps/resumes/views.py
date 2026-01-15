"""
이력서 뷰
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.jobs.models import JobPosting
from .models import Resume, ResumeMatching
from .serializers import ResumeSerializer, ResumeDetailSerializer, ResumeMatchingSerializer
from django.db import transaction


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

        try:
            job_posting = JobPosting.objects.get(
                pk=job_posting_id,
                is_deleted=False
            )
        except JobPosting.DoesNotExist:
            return Response(
                {'error': '채용 공고를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: 매칭 로직 구현 (Celery 태스크로 처리)
        # 현재는 더미 데이터로 ResumeMatching 생성
        matching = ResumeMatching.objects.create(
            resume=resume,
            job_posting=job_posting,
            score=75.50,
            feedback='클라우드 경험을 추가하면 매칭률이 높아질 것입니다.',
            question='Django ORM의 장단점에 대해 설명해주세요.'
        )

        return Response(ResumeMatchingSerializer(matching).data, status=status.HTTP_201_CREATED)


class ResumeMatchingListView(generics.ListAPIView):
    """이력서 매칭 목록 조회"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeMatchingSerializer

    def get_queryset(self):
        return ResumeMatching.objects.filter(
            resume__user=self.request.user,
            is_deleted=False
        ).select_related('job_posting', 'resume')


class ResumeMatchingDetailView(generics.RetrieveAPIView):
    """이력서 매칭 상세 조회"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeMatchingSerializer

    def get_queryset(self):
        return ResumeMatching.objects.filter(
            resume__user=self.request.user,
            is_deleted=False
        ).select_related('job_posting', 'resume')


class ResumeRestoreView(APIView):
    """이력서 복원 (분석 내용 및 면접 질문 포함)"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        """
        삭제된 이력서를 복원합니다.
        이력서와 함께 관련된 분석 내용(ResumeMatching)도 복원됩니다.
        """
        try:
            resume = Resume.objects.get(
                pk=pk,
                user=request.user,
                is_deleted=True
            )
        except Resume.DoesNotExist:
            return Response(
                {'error': '삭제된 이력서를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 트랜잭션으로 이력서와 관련 매칭 정보를 함께 복원
        with transaction.atomic():
            # 이력서 복원
            resume.is_deleted = False
            resume.save()

            # 관련된 분석 내용 및 면접 질문(ResumeMatching) 복원
            restored_count = ResumeMatching.objects.filter(
                resume=resume,
                is_deleted=True
            ).update(is_deleted=False)

        return Response({
            'message': '이력서가 성공적으로 복원되었습니다.',
            'resume_id': resume.id,
            'resume_title': resume.title,
            'restored_matchings': restored_count
        }, status=status.HTTP_200_OK)
