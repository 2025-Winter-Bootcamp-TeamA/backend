from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from apps.jobs.models import JobPosting
from apps.trends.models import TechStack
from .models import Resume, ResumeMatching, ResumeStack, WorkExperience, ProjectExperience, ResumeExtractedStack
from .serializers import ResumeSerializer, ResumeDetailSerializer, ResumeMatchingSerializer, WorkExperienceSerializer, ProjectExperienceSerializer
from .utils import analyze_resume
from django.db import transaction
from decouple import config
import os
import json
import re # ✅ 추가: 정규식 사용을 위해 필요
import traceback # ✅ 추가: 상세 에러 로그 출력을 위해 필요
import google.genai as genai
from django.conf import settings
from scripts.pdf_text_extractor import extract_text_from_pdf_url
from celery.result import AsyncResult
from .tasks import analyze_resume_task


class ResumeListCreateView(generics.ListCreateAPIView):
    """이력서 목록 조회 및 생성(PDF 업로드) - 전체 반환"""
    permission_classes = [IsAuthenticated]
    pagination_class = None  # 페이지네이션 비활성화
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
        return Resume.objects.filter(
            user=self.request.user, 
            is_deleted=False
        ).prefetch_related(
            'work_experiences',
            'project_experiences',
            'tech_stacks__tech_stack'
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # DB에 저장된 work_experiences와 project_experiences 데이터 가져오기
        work_experiences = WorkExperience.objects.filter(resume=instance)
        project_experiences = ProjectExperience.objects.filter(resume=instance)

        # 기술 스택 정보 가져오기
        try:
            extracted_stack = ResumeExtractedStack.objects.get(resume=instance)
            has_extracted_data = True
        except ResumeExtractedStack.DoesNotExist:
            has_extracted_data = False

        extracted_text = None

        # DB에 구조화된 데이터가 있으면 포맷팅하여 사용
        if has_extracted_data or work_experiences.exists() or project_experiences.exists():
            formatted_text_parts = []

            # 직무 경험 추가
            if work_experiences.exists():
                formatted_text_parts.append('직무 경험:\n\n')
                for exp in work_experiences:
                    formatted_text_parts.append(f"{exp.organization}\n")
                    # details가 문자열이면 줄바꿈으로 분리
                    if isinstance(exp.details, str):
                        details_list = [d.strip() for d in exp.details.split('\n') if d.strip()]
                    else:
                        details_list = []

                    for detail in details_list:
                        formatted_text_parts.append(f"• {detail}\n")
                    formatted_text_parts.append('\n')

            # 프로젝트 경험 추가
            if project_experiences.exists():
                formatted_text_parts.append('프로젝트 경험:\n\n')
                for exp in project_experiences:
                    formatted_text_parts.append(f"{exp.project_name}\n")
                    if exp.context:
                        formatted_text_parts.append(f"{exp.context}\n\n")

                    # details가 문자열이면 줄바꿈으로 분리
                    if isinstance(exp.details, str):
                        details_list = [d.strip() for d in exp.details.split('\n') if d.strip()]
                    else:
                        details_list = []

                    for detail in details_list:
                        formatted_text_parts.append(f"• {detail}\n")
                    formatted_text_parts.append('\n')

            # 합쳐진 텍스트 생성
            if formatted_text_parts:
                extracted_text = ''.join(formatted_text_parts).strip()

        # DB에 구조화된 데이터가 없으면 PDF에서 추출
        if not extracted_text and instance.url:
            try:
                pdf_url = instance.url
                if pdf_url.startswith('/'):
                    pdf_url = request.build_absolute_uri(pdf_url)
                resume_text = extract_text_from_pdf_url(pdf_url)
                if resume_text and resume_text.strip():
                    extracted_text = resume_text
            except Exception as e:
                # 텍스트 추출 실패해도 에러 없이 진행
                pass

        # 인스턴스에 추출된 텍스트를 임시로 저장 (serializer에서 사용)
        instance._extracted_text = extracted_text

        serializer = self.get_serializer(instance)
        data = serializer.data

        # serializer에서 None이면 직접 설정
        if extracted_text and not data.get('extracted_text'):
            data['extracted_text'] = extracted_text

        return Response(data)

    def perform_destroy(self, instance):
        # 삭제 시 관련된 분석 데이터도 함께 Soft Delete
        with transaction.atomic():
            instance.is_deleted = True
            instance.save()

            ResumeMatching.objects.filter(
                resume=instance,
                is_deleted=False
            ).update(is_deleted=True)
        

class ResumeMatchingView(APIView):
    """이력서와 채용 공고 매칭 (Gemini Pro) - JSON 파싱 강화 버전"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, job_posting_id):
        # 1. 데이터 조회
        try:
            resume = Resume.objects.get(pk=pk, user=request.user, is_deleted=False)
            job_posting = JobPosting.objects.get(pk=job_posting_id, is_deleted=False)
        except (Resume.DoesNotExist, JobPosting.DoesNotExist):
            return Response({'error': '이력서 또는 채용 공고를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 2. API 키 확인
        if not settings.GOOGLE_GEMINI_API_KEY:
            return Response({'error': 'GOOGLE_GEMINI_API_KEY 설정이 누락되었습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # 새로운 google.genai SDK 사용
            client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)

            # 3. 프롬프트 데이터 구성
            job_description = job_posting.description
            
            work_experiences = WorkExperience.objects.filter(resume=resume)
            project_experiences = ProjectExperience.objects.filter(resume=resume)
            try:
                extracted_stack = ResumeExtractedStack.objects.get(resume=resume)
                stacks_info = f"보유 기술: {', '.join(extracted_stack.technical_tools)}\n방법론: {', '.join(extracted_stack.methodologies)}\n기타: {', '.join(extracted_stack.others)}"
            except ResumeExtractedStack.DoesNotExist:
                stacks_info = "추출된 기술 스택 정보가 없습니다."

            work_exp_str = "\n".join([f"- {w.organization}: {w.details}" for w in work_experiences])
            proj_exp_str = "\n".join([f"- {p.project_name}: {p.context}\n  {p.details}" for p in project_experiences])

            # Gemini에 전달할 프롬프트 (JSON 형식 대신 커스텀 태그 사용)
            prompt = f"""
            # Role
            당신은 세계적인 빅테크 기업의 시니어 기술 면접관이자 아키텍트입니다. 
            주어진 채용 공고(JD)의 요구사항과 지원자의 기술 스택/경험을 대조하여, '기술적 진실성'과 '경험의 깊이'를 날카롭게 파고드는 면접 질문을 생성하십시오.

            # Input Data
            1. 채용 공고 (JD): {job_description}
            2. 지원자 직무 경험: {work_exp_str}
            3. 지원자 프로젝트 경험: {proj_exp_str}
            4. 보유 기술 스택: {stacks_info}

            # 기술 면접 참고 주제 (지원자의 기술 스택과 관련된 주제 중심으로 질문 생성)
            - Computer Science: 자료구조(Array, LinkedList, Stack, Queue, Hash, Tree, Graph), 알고리즘(정렬, 탐색, DP)
            - 운영체제: 프로세스 vs 스레드, 교착상태(DeadLock), 동기화(Mutex, Semaphore), 메모리 관리, CPU 스케줄링
            - 네트워크: OSI 7계층, TCP/UDP, HTTP/HTTPS, REST API, 로드밸런싱, 쿠키/세션
            - 데이터베이스: SQL vs NoSQL, 인덱스, 트랜잭션, 정규화, JOIN, Redis
            - 웹: 브라우저 동작원리, CSR/SSR, JWT, OAuth, CSRF/XSS
            - 언어별: Java(JVM, GC, 멀티스레드), Python(GIL), JavaScript(이벤트루프, 클로저)
            - Spring: Bean, MVC, JPA, 트랜잭션, Security
            - DevOps: Docker, Kubernetes, CI/CD, 모니터링

            # Analysis Task
            1. [역량 대조]: JD 핵심 기술과 지원자의 숙련도를 추론하십시오.
            2. [강점과 약점]: 기술적 적합성이 높은 부분(Positive)과 부족한 부분(Negative)을 도출하십시오.
            3. [보완할 점]: JD와의 간극을 메우기 위해 학습해야 할 기술/개념을 제안하십시오.
            4. [면접 질문]: 위 분석 결과와 기술 면접 참고 주제를 바탕으로, 지원자의 경험과 연관된 기술 심화 질문 5개를 생성하십시오.

            # Output Format (Strict Custom Tags)
            절대 JSON을 사용하지 마십시오. 반드시 아래 제공된 커스텀 태그 형식으로만 응답해야 합니다. 각 태그 사이에 내용을 채워주세요.
            각 feedback은 글머리 기호(•)를 사용하여 2-4개의 항목으로 작성하고, 각 항목은 50자 내외로 핵심만 간결하게 작성하십시오.
            질문은 100자 내외로 핵심을 짚는 간결한 질문을 생성하십시오.
            모범 답변은 지원자의 경험을 바탕으로 100자 내외로 핵심 포인트만 간결하게 작성하십시오.

            [POSITIVE_FEEDBACK_START]
            • (강점 1 - 50자 내외)
            • (강점 2 - 50자 내외)
            • (강점 3 - 50자 내외)
            [POSITIVE_FEEDBACK_END]

            [NEGATIVE_FEEDBACK_START]
            • (약점 1 - 50자 내외)
            • (약점 2 - 50자 내외)
            • (약점 3 - 50자 내외)
            [NEGATIVE_FEEDBACK_END]

            [ENHANCEMENTS_START]
            • (보완점 1 - 50자 내외)
            • (보완점 2 - 50자 내외)
            • (보완점 3 - 50자 내외)
            [ENHANCEMENTS_END]

            [QUESTION_1_START]
            (질문 1)
            [QUESTION_1_END]
            [ANSWER_1_START]
            (질문 1에 대한 모범 답변)
            [ANSWER_1_END]

            [QUESTION_2_START]
            (질문 2)
            [QUESTION_2_END]
            [ANSWER_2_START]
            (질문 2에 대한 모범 답변)
            [ANSWER_2_END]

            [QUESTION_3_START]
            (질문 3)
            [QUESTION_3_END]
            [ANSWER_3_START]
            (질문 3에 대한 모범 답변)
            [ANSWER_3_END]

            [QUESTION_4_START]
            (질문 4)
            [QUESTION_4_END]
            [ANSWER_4_START]
            (질문 4에 대한 모범 답변)
            [ANSWER_4_END]

            [QUESTION_5_START]
            (질문 5)
            [QUESTION_5_END]
            [ANSWER_5_START]
            (질문 5에 대한 모범 답변)
            [ANSWER_5_END]
            """

            # 4. Gemini API 호출
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text

            # 5. 커스텀 태그 기반 파싱 로직
            def extract_text_between_tags(text, start_tag, end_tag):
                start_index = text.find(start_tag)
                if start_index == -1: return ""
                end_index = text.find(end_tag, start_index)
                if end_index == -1: return ""
                return text[start_index + len(start_tag):end_index].strip()

            positive_feedback = extract_text_between_tags(raw_text, '[POSITIVE_FEEDBACK_START]', '[POSITIVE_FEEDBACK_END]')
            negative_feedback = extract_text_between_tags(raw_text, '[NEGATIVE_FEEDBACK_START]', '[NEGATIVE_FEEDBACK_END]')
            enhancements_feedback = extract_text_between_tags(raw_text, '[ENHANCEMENTS_START]', '[ENHANCEMENTS_END]')
            
            questions = []
            answers = []
            for i in range(1, 6):
                question = extract_text_between_tags(raw_text, f'[QUESTION_{i}_START]', f'[QUESTION_{i}_END]')
                answer = extract_text_between_tags(raw_text, f'[ANSWER_{i}_START]', f'[ANSWER_{i}_END]')
                if question:
                    questions.append(question)
                    answers.append(answer if answer else "답변 없음")
            
            if not positive_feedback and not negative_feedback and not questions:
                 return Response({'error': 'AI 응답에서 유효한 내용을 추출할 수 없습니다. 형식이 다를 수 있습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            question_str = "\n".join([f"- {q}" for q in questions])
            answer_str = "\n".join([f"- {a}" for a in answers])

            # 6. 데이터 저장
            matching, created = ResumeMatching.objects.update_or_create(
                resume=resume,
                job_posting=job_posting,
                defaults={
                    'positive_feedback': positive_feedback or "정보 없음",
                    'negative_feedback': negative_feedback or "정보 없음",
                    'enhancements_feedback': enhancements_feedback or "정보 없음",
                    'question': question_str,
                    'answer': answer_str,
                }
            )
            
            serializer = ResumeMatchingSerializer(matching)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            print("\n" + "="*50)
            print("🚨 ResumeMatchingView Error Traceback:")
            traceback.print_exc()
            print("="*50 + "\n")
            return Response({'error': f'서버 내부 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResumeMatchingListView(generics.ListAPIView):
    """이력서 매칭 목록 조회 - 전체 반환"""
    permission_classes = [IsAuthenticated]
    pagination_class = None  # 페이지네이션 비활성화
    serializer_class = ResumeMatchingSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ResumeMatching.objects.none()
        return ResumeMatching.objects.filter(
            resume__user=self.request.user,
            is_deleted=False
        ).select_related('job_posting', 'resume').order_by('-id')


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

        return Response({
            'message': '이력서가 성공적으로 복원되었습니다.',
            'resume_id': resume.id,
            'resume_title': resume.title,
            'restored_matchings': restored_count
        }, status=status.HTTP_200_OK)


class ResumeAnalyzeView(APIView):
    """이력서 분석 및 직무/프로젝트 경험 추출 (비동기)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, resume_id):
        try:
            resume = Resume.objects.get(pk=resume_id, user=request.user, is_deleted=False)
        except Resume.DoesNotExist:
            return Response({'error': '이력서를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if not resume.url:
            return Response({'error': '이력서 URL이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 브라우저가 접근 가능한 절대 URL 생성
        pdf_url = resume.url
        if pdf_url.startswith('/'):
            pdf_url = request.build_absolute_uri(pdf_url)

        # 2. Docker 내부 통신용 URL로 변환 (Celery Worker가 접근할 수 있도록)
        #    Celery 컨테이너는 'localhost'가 아닌 'backend' 서비스 이름으로 웹서버에 접근해야 함
        internal_pdf_url = pdf_url.replace('localhost', 'backend').replace('127.0.0.1', 'backend')

        # 디버그 로그 추가
        print(f"DEBUG: Passing URL to Celery: {internal_pdf_url}")

        # Celery 작업을 호출하여 비동기적으로 분석 실행 (내부 URL 전달)
        task = analyze_resume_task.delay(resume.id, internal_pdf_url)

        # 클라이언트에게 작업이 시작되었음을 알림
        return Response(
            {'message': '이력서 분석 작업이 시작되었습니다.', 'task_id': task.id},
            status=status.HTTP_202_ACCEPTED
        )


class ResumeAnalysisStatusView(APIView):
    """Celery 작업 상태 및 결과 확인"""
    permission_classes = []  # 태스크 ID는 추측이 거의 불가능하므로 인증 없이 허용

    def get(self, request, task_id):
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.state,
            'result': None
        }

        if task_result.successful():
            # 작업이 성공적으로 완료되었을 때 결과
            response_data['result'] = task_result.get()
        elif task_result.failed():
            # 작업 실패 시 에러 정보
            response_data['result'] = str(task_result.info)  # 에러 메시지
        
        return Response(response_data)