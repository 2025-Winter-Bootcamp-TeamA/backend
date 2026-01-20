from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from apps.jobs.models import JobPosting
from apps.trends.models import TechStack
from .models import Resume, ResumeMatching, ResumeStack
from .serializers import ResumeSerializer, ResumeDetailSerializer, ResumeMatchingSerializer
from .utils import analyze_resume
from django.db import transaction
from decouple import config

class ResumeListCreateView(generics.ListCreateAPIView):
    """이력서 목록 조회 및 생성(PDF 업로드)"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Resume.objects.none()
        return Resume.objects.filter(user=self.request.user, is_deleted=False)

    def perform_create(self, serializer):
        serializer.save()

class ResumeDetailView(generics.RetrieveDestroyAPIView):
    """이력서 상세 조회/삭제"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeDetailSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Resume.objects.none()
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
    """이력서 분석 (AI 기반) - Ollama Gemma3:12b 모델 사용"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """
        S3에서 PDF를 다운로드하고, 텍스트를 추출한 후, 
        Ollama Gemma3:12b로 기술 스택을 추출하여 저장합니다.
        """
        try:
            # 1. 이력서 조회
            resume = Resume.objects.get(pk=pk, user=request.user, is_deleted=False)
            
            if not resume.url:
                return Response(
                    {"error": "이력서 파일이 업로드되지 않았습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 2. Ollama URL 설정 (환경변수 또는 기본값)
            ollama_url = config('OLLAMA_URL', default='http://localhost:11434')
            
            # 3. 이력서 분석 (S3 다운로드 → PDF 텍스트 추출 → Ollama 분석)
            try:
                resume_text, tech_stack_names = analyze_resume(resume.url, ollama_url)
            except Exception as e:
                return Response(
                    {"error": f"이력서 분석 실패: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 4. 기존 기술 스택 삭제 후 새로 저장
            with transaction.atomic():
                # 기존 기술 스택 삭제
                ResumeStack.objects.filter(resume=resume).delete()
                
                # 새로운 기술 스택 저장
                created_count = 0
                for tech_name in tech_stack_names:
                    try:
                        tech_stack = TechStack.objects.get(name__iexact=tech_name)
                        ResumeStack.objects.create(
                            resume=resume,
                            tech_stack=tech_stack
                        )
                        created_count += 1
                    except TechStack.DoesNotExist:
                        continue
            
            return Response({
                "message": "이력서 분석이 완료되었습니다.",
                "resume_id": resume.id,
                "resume_title": resume.title,
                "extracted_tech_count": created_count,
                "tech_stacks": tech_stack_names
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response(
                {"error": "이력서를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

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
        if getattr(self, 'swagger_fake_view', False):
            return ResumeMatching.objects.none()
        return ResumeMatching.objects.filter(
            resume__user=self.request.user,
            is_deleted=False
        ).select_related('job_posting', 'resume')


class ResumeMatchingDetailView(generics.RetrieveAPIView):
    """이력서 매칭 상세 조회"""
    permission_classes = [IsAuthenticated]
    serializer_class = ResumeMatchingSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ResumeMatching.objects.none()
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

        # 주석
        return Response({
            'message': '이력서가 성공적으로 복원되었습니다.',
            'resume_id': resume.id,
            'resume_title': resume.title,
            'restored_matchings': restored_count
        }, status=status.HTTP_200_OK)
    