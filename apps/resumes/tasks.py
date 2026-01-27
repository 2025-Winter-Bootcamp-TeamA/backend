from celery import shared_task
from django.db import transaction
from .models import Resume, ResumeStack, WorkExperience, ProjectExperience, ResumeExtractedStack
from scripts.pdf_text_extractor import extract_text_from_pdf_url
from scripts.module_resume_extractor import ResumeParserSystem
import logging
from django.conf import settings
logger = logging.getLogger(__name__)

@shared_task
def analyze_resume_task(resume_id, pdf_url):
    """
    Celery task to analyze a resume asynchronously.
    """
    from apps.trends.models import TechStack

    try:
        resume = Resume.objects.get(pk=resume_id)
    except Resume.DoesNotExist:
        logger.error(f"Resume with id {resume_id} not found.")
        return

    try:
        # 1. Extract text from PDF using the provided absolute URL
        resume_text = extract_text_from_pdf_url(pdf_url)
        if not resume_text or not resume_text.strip():
            logger.error(f"Could not extract text from PDF for resume {resume_id} using URL {pdf_url}.")
            # Optionally, update resume status to 'failed'
            return

        # 2. Analyze with AI model
        ollama_host = settings.OLLAMA_URL
        parser = ResumeParserSystem(host=ollama_host)
        structured_data = parser.parse(resume_text)

        # 3. Update database
        with transaction.atomic():
            WorkExperience.objects.filter(resume=resume).delete()
            ProjectExperience.objects.filter(resume=resume).delete()
            ResumeExtractedStack.objects.filter(resume=resume).delete()

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

            # 4. ResumeStack 모델에 실제 TechStack 연결 (추가)
            # 대소문자 구분 없이 DB의 TechStack과 매칭 시도
            for tool_name in all_technical_tools:
                tech_stack = TechStack.objects.filter(name__iexact=tool_name).first()
                if tech_stack:
                    ResumeStack.objects.get_or_create(resume=resume, tech_stack=tech_stack)
        
        logger.info(f"Successfully analyzed and updated resume {resume_id}.")
        return {'resume_id': resume_id, 'status': 'SUCCESS'}

    except Exception as e:
        logger.error(f"An error occurred during resume analysis for resume {resume_id}: {str(e)}", exc_info=True)
        # 작업 실패 시 예외를 다시 발생시켜 Celery가 실패 상태로 처리하도록 함
        raise
