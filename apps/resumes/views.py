from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from apps.jobs.models import JobPosting
from .models import Resume, ResumeMatching
from .serializers import (
    ResumeSerializer, 
    ResumeDetailSerializer, 
    ResumeMatchingSerializer
)

class ResumeListCreateView(generics.ListCreateAPIView):
    """이력서 목록 조회 및 생성(PDF 업로드)"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user, is_deleted=False)

    def perform_create(self, serializer):
        serializer.save()

class ResumeDetailView(generics.RetrieveDestroyAPIView):
    """이력서 상세 조회/삭제"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeDetailSerializer

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user, is_deleted=False)

    def perform_destroy(self, instance):
        # 삭제 시 관련된 분석 데이터도 함께 Soft Delete
        with transaction.atomic():
            instance.is_deleted = True
            instance.save()

            ResumeMatching.objects.filter(
                resume=instance,
                is_deleted=False
            ).update(is_deleted=True)
        


class ResumeAnalyzeView(APIView):
    """이력서 분석 (AI 기반) - 현재는 준비 중 응답"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return Response({"message": "분석 기능이 준비 중입니다."}, status=status.HTTP_202_ACCEPTED)

class ResumeMatchingView(APIView):
    """이력서와 채용 공고 매칭"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, job_posting_id):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user, is_deleted=False)
            job_posting = JobPosting.objects.get(pk=job_posting_id, is_deleted=False)
            
            # 더미 매칭 데이터 생성
            matching = ResumeMatching.objects.create(
                resume=resume,
                job_posting=job_posting,
                score=0.00,
                feedback='분석 로직 대기 중입니다.',
                question='준비 중인 질문입니다.'
            )
            return Response(ResumeMatchingSerializer(matching).data, status=status.HTTP_201_CREATED)
        except (Resume.DoesNotExist, JobPosting.DoesNotExist):
            return Response({'error': '데이터를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

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
        )