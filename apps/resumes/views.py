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
                resume_text = extract_text_from_pdf_url(instance.url)
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

import json
import google.generativeai as genai
from django.conf import settings

class ResumeMatchingView(APIView):
    """이력서와 채용 공고 매칭 (Gemini Pro)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, job_posting_id):
        try:
            resume = Resume.objects.get(pk=pk, user=request.user, is_deleted=False)
            job_posting = JobPosting.objects.get(pk=job_posting_id, is_deleted=False)
        except (Resume.DoesNotExist, JobPosting.DoesNotExist):
            return Response({'error': '이력서 또는 채용 공고를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # Gemini API 설정
        if not settings.GOOGLE_GEMINI_API_KEY:
            return Response({'error': 'GOOGLE_GEMINI_API_KEY가 설정되지 않았습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)

            # 프롬프트에 사용할 데이터 준비
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

            # Gemini에 전달할 프롬프트 구성 (한국어)
            prompt = f"""
                        # Role
                        당신은 세계적인 빅테크 기업의 시니어 기술 면접관이자 아키텍트입니다. 
                        주어진 채용 공고(JD)의 요구사항과 지원자의 기술 스택/경험을 대조하여, '기술적 진실성'과 '경험의 깊이'를 날카롭게 파고드는 면접 질문을 생성하십시오.

                        # Context
                        지원자의 연차, 학력, 수상 경력과 같은 정적 정보는 무시합니다. 오직 '기술적 역량'과 '프로젝트 수행 능력'에만 집중하십시오. 지원자가 사용한 기술들 사이의 관계(예: 왜 이 DB를 선택했는지, 특정 라이브러리를 사용한 이유가 무엇인지)를 심층 분석해야 합니다.

                        # Input Data
                        1. 채용 공고 (JD): {job_description}
                        2. 지원자 직무 경험: {work_exp_str}
                        3. 지원자 프로젝트 경험: {proj_exp_str}
                        4. 보유 기술 스택: {stacks_info}

                        # Analysis Task
                        1. [역량 대조]: JD에서 요구하는 핵심 기술과 지원자가 보유한 기술의 '숙련도'를 추론하십시오. 단순히 키워드가 일치하는지가 아니라, 실제 프로젝트에서 어떤 '맥락'으로 사용되었는지 분석합니다.
                        2. [강점과 약점]: 기술적 적합성이 높은 부분(Positive)과, 기술적 깊이가 검증되지 않았거나 JD 대비 부족한 부분(Negative)을 도출하십시오.
                        3. [보완할 점]: JD와의 기술적 간극을 메우기 위해, 지원자가 추가로 학습하거나 경험해야 할 기술/개념을 제안하십시오.
                        4. [가변적 질문 생성]: 다음 3가지 유형을 섞어 5~7개의 질문을 생성하십시오.
                        - Deep Dive: 지원자가 사용한 특정 기술의 내부 동작 원리나 최적화 경험 질문
                        - Trade-off: 왜 다른 대안(A) 대신 이 기술(B)을 선택했는지에 대한 논리적 근거 질문
                        - Scenario-based: JD의 기술 환경에서 발생할 수 있는 가상의 기술적 난관을 제시하고 해결 방법 질문

                        # Output Format (Strict JSON)
                        반드시 아래 JSON 형식을 유지하며, 모든 답변은 한국어로 작성하십시오.

                        {{
                            "feedback": {{
                                "positive": "제한된 형식 없이, 지원자의 기술적 강점과 프로젝트의 성숙도를 엔지니어링 관점에서 자유롭게 서술하십시오.",
                                "negative": "JD와의 기술적 간극, 잠재적 리스크, 기술적 깊이가 우려되는 지점을 날카로운 비평 형태로 자유롭게 서술하십시오."
                                "enhancements": "지원자가 보완해야 할 기술적 역량이나 개념을 구체적으로 제안하십시오."
                            }},
                            "questions": [
                            "질문 1 (기술의 본질과 원리 파악)",
                            "질문 2 (의사결정 과정 및 기술 선택의 이유)",
                            "질문 3 (성능 최적화 또는 트러블슈팅 경험)",
                            "질문 4 (JD 환경에 특화된 가상 시나리오 대응)",
                            "질문 5 (기술 스택 간의 상호작용 및 아키텍처 이해도)"
                            ]
                        }}
            """

            # Gemini API 호출
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content(prompt)
            
            response_text = ''.join(part.text for part in response.parts)
            cleaned_response_text = response_text.strip().replace('```json', '').replace('```', '')
            
            print("--- Gemini API Response for JSON Parsing ---")
            print(f"Response to be parsed: '{cleaned_response_text}'")
            print("------------------------------------------")

            response_json = json.loads(cleaned_response_text)
            
            feedback_json = response_json.get("feedback", {})
            positive_feedback = feedback_json.get("positive", "긍정적 피드백을 생성하지 못했습니다.")
            negative_feedback = feedback_json.get("negative", "부정적 피드백을 생성하지 못했습니다.")
            enhancements_feedback = feedback_json.get("enhancements", "보완할 점 피드백을 생성하지 못했습니다.")
            questions = response_json.get("questions", [])
            question_str = "\n".join([f"- {q}" for q in questions])

            # 결과 저장 (update_or_create 사용)
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
            return Response({'error': f'매칭 데이터 생성 중 오류 발생: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class ResumeMatchCreateAPIView(APIView):
    """이력서 분석 및 직무/프로젝트 경험 추출"""
    permission_classes = [IsAuthenticated]

    def post(self, request, resume_id):
        try:
            resume = Resume.objects.get(pk=resume_id, user=request.user, is_deleted=False)
        except Resume.DoesNotExist:
            return Response({'error': '이력서를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if not resume.url:
            return Response({'error': '이력서 URL이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resume_text = extract_text_from_pdf_url(resume.url)
            if not resume_text or not resume_text.strip():
                return Response({'error': 'PDF에서 텍스트를 추출할 수 없었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            ollama_host = 'http://host.docker.internal:11434' if os.path.exists('/.dockerenv') else config('OLLAMA_URL', default='http://localhost:11434')
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