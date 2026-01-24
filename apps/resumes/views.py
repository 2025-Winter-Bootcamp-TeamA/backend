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
from scripts.module_resume_extractor import ResumeParserSystem


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
        
        # 텍스트로 포맷팅
        formatted_text_parts = []
        
        # 직무 경험 추가
        if work_experiences.exists():
            formatted_text_parts.append('직무 경험:\n')
            for exp in work_experiences:
                formatted_text_parts.append(f"{exp.organization}: {exp.details}\n")
            formatted_text_parts.append('\n')
        
        # 프로젝트 경험 추가
        if project_experiences.exists():
            formatted_text_parts.append('프로젝트 경험:\n')
            for exp in project_experiences:
                formatted_text_parts.append(f"{exp.project_name}\n{exp.context}\n{exp.details}\n\n")
        
        # 합쳐진 텍스트 생성
        extracted_text = ''.join(formatted_text_parts).strip() if formatted_text_parts else None
        
        # DB 데이터가 없으면 원본 PDF에서 추출 시도
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

            # Gemini에 전달할 프롬프트
            prompt = f"""
            # Role
            당신은 세계적인 빅테크 기업의 시니어 기술 면접관이자 아키텍트입니다. 
            주어진 채용 공고(JD)의 요구사항과 지원자의 기술 스택/경험을 대조하여, '기술적 진실성'과 '경험의 깊이'를 날카롭게 파고드는 면접 질문을 생성하십시오.

            # Input Data
            1. 채용 공고 (JD): {job_description}
            2. 지원자 직무 경험: {work_exp_str}
            3. 지원자 프로젝트 경험: {proj_exp_str}
            4. 보유 기술 스택: {stacks_info}

            # Analysis Task
            1. [역량 대조]: JD 핵심 기술과 지원자의 숙련도를 추론하십시오.
            2. [강점과 약점]: 기술적 적합성이 높은 부분(Positive)과 부족한 부분(Negative)을 도출하십시오.
            3. [보완할 점]: JD와의 간극을 메우기 위해 학습해야 할 기술/개념을 제안하십시오.
            4. [면접 질문]: Deep Dive, Trade-off, Scenario 유형을 섞어 5개의 질문을 생성하십시오.

            # Output Format (Strict JSON)
            반드시 아래 JSON 형식을 준수해야 합니다. 마크다운 기호(```)나 잡담을 포함하지 마십시오.

            {{
                "feedback": {{
                    "positive": "지원자의 강점 서술",
                    "negative": "부족한 점 및 리스크 서술",
                    "enhancements": "보완할 점 서술"
                }},
                "questions": [
                    "질문 1",
                    "질문 2",
                    "질문 3",
                    "질문 4",
                    "질문 5"
                ]
            }}
            """

            # 4. Gemini API 호출 (gemini-1.5-flash deprecated → gemini-2.5-flash 사용)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )

            raw_text = response.text
            print(f"🔹 [Gemini Response Raw]: {raw_text[:100]}...") # 로그 확인용

            # 5. JSON 추출 로직 (정규식 사용)
            # 중괄호로 둘러싸인 JSON 부분만 추출하여 파싱 에러 방지
            json_match = re.search(r'\{[\s\S]*\}', raw_text)
            
            if not json_match:
                print("❌ JSON 형식을 찾을 수 없습니다.")
                return Response({'error': 'AI 응답에서 데이터를 추출할 수 없습니다. (JSON 형식 불일치)'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            cleaned_json_text = json_match.group(0)

            try:
                response_json = json.loads(cleaned_json_text)
            except json.JSONDecodeError as e:
                print(f"❌ JSON 파싱 에러: {str(e)}")
                print(f"❌ 파싱 시도 텍스트: {cleaned_json_text}")
                return Response({'error': f'AI 데이터 파싱 실패: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 6. 데이터 추출 및 저장
            feedback_json = response_json.get("feedback", {})
            positive_feedback = feedback_json.get("positive", "정보 없음")
            negative_feedback = feedback_json.get("negative", "정보 없음")
            enhancements_feedback = feedback_json.get("enhancements", "정보 없음")
            
            questions = response_json.get("questions", [])
            question_str = "\n".join([f"- {q}" for q in questions])

            matching, created = ResumeMatching.objects.update_or_create(
                resume=resume,
                job_posting=job_posting,
                defaults={
                    'positive_feedback': positive_feedback,
                    'negative_feedback': negative_feedback,
                    'enhancements_feedback': enhancements_feedback,
                    'question': question_str,
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
    """이력서 매칭 목록 조회"""
    permission_classes = [IsAuthenticated]
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
    """이력서 분석 및 직무/프로젝트 경험 추출"""
    permission_classes = [IsAuthenticated]

    def post(self, request, resume_id):
        try:
            resume = Resume.objects.get(pk=resume_id, user=request.user, is_deleted=False)
        except Resume.DoesNotExist:
            return Response({'error': '이력서를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if not resume.url:
            return Response({'error': '이력서 URL이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 상대 경로(/media/...)는 requests.get()에서 쓸 수 있도록 절대 URL로 변환
        pdf_url = resume.url
        if pdf_url.startswith('/'):
            pdf_url = request.build_absolute_uri(pdf_url)

        try:
            resume_text = extract_text_from_pdf_url(pdf_url)
            if not resume_text or not resume_text.strip():
                return Response({'error': 'PDF에서 텍스트를 추출할 수 없었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            ollama_host= 'http://host.docker.internal:11434'

            #ollama_host = settings.OLLAMA_URL
            parser = ResumeParserSystem(host=ollama_host)
            structured_data = parser.parse(resume_text)

            with transaction.atomic():
                WorkExperience.objects.filter(resume=resume).delete()
                ProjectExperience.objects.filter(resume=resume).delete()
                ResumeExtractedStack.objects.filter(resume=resume).delete() # Delete existing extracted stack

                if 'work_experience' in structured_data and structured_data['work_experience']:
                    for exp in structured_data['work_experience']:
                        WorkExperience.objects.create(
                            resume=resume,
                            organization=exp.get('organization') or '',
                            details=exp.get('details') or ''
                        )

                if 'project_experience' in structured_data and structured_data['project_experience']:
                    for exp in structured_data['project_experience']:
                        ProjectExperience.objects.create(
                            resume=resume,
                            project_name=exp.get('name') or '',
                            context=exp.get('context') or '',
                            details=exp.get('details') or ''
                        )

                # Extract and combine technical tools, methodologies, and others
                all_technical_tools = set()
                methodologies = []
                others = []

                if 'project_experience' in structured_data and structured_data.get('project_experience'):
                    for exp in structured_data['project_experience']:
                        if 'tools' in exp and isinstance(exp['tools'], list):
                            all_technical_tools.update(tool for tool in exp['tools'] if isinstance(tool, str))

                if 'key_capabilities' in structured_data and structured_data.get('key_capabilities'):
                    key_capabilities = structured_data['key_capabilities']
                    if 'technical_tools' in key_capabilities and isinstance(key_capabilities['technical_tools'], list):
                        all_technical_tools.update(tool for tool in key_capabilities['technical_tools'] if isinstance(tool, str))
                    if 'methodologies' in key_capabilities and isinstance(key_capabilities['methodologies'], list):
                        methodologies = [m for m in key_capabilities['methodologies'] if isinstance(m, str)]
                    if 'others' in key_capabilities and isinstance(key_capabilities['others'], list):
                        others = [o for o in key_capabilities['others'] if isinstance(o, str)]

                ResumeExtractedStack.objects.create(
                    resume=resume,
                    technical_tools=list(all_technical_tools),
                    methodologies=methodologies,
                    others=others
                )

            return Response({'message': '분석 완료'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'분석 중 오류 발생: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)