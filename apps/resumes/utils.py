"""
이력서 처리 유틸리티
- S3에서 PDF 다운로드
- PDF 텍스트 추출
- Ollama를 통한 기술 스택 추출
"""

import io
import json
import requests
from PyPDF2 import PdfReader
from django.conf import settings
from decouple import config
from apps.trends.models import TechStack


def download_pdf_from_s3(s3_url):
    """
    S3 URL에서 PDF 파일을 다운로드
    Public 버킷은 HTTP GET으로 직접 다운로드
    
    Args:
        s3_url (str): S3 파일 URL
        
    Returns:
        bytes: PDF 파일 바이너리 데이터
    """
    try:
        # Public 버킷이므로 HTTP GET으로 직접 다운로드
        response = requests.get(s3_url, timeout=30)
        
        if response.status_code == 403:
            raise Exception("S3 접근 권한이 없습니다. 버킷이 Public인지 확인하세요.")
        elif response.status_code == 404:
            raise Exception("S3 파일을 찾을 수 없습니다.")
        elif response.status_code != 200:
            raise Exception(f"S3 다운로드 실패: HTTP {response.status_code}")
        
        return response.content
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"S3에서 PDF 다운로드 실패: {str(e)}")


def extract_text_from_pdf(pdf_data):
    """
    PDF 바이너리 데이터에서 텍스트 추출
    
    Args:
        pdf_data (bytes): PDF 파일 바이너리 데이터
        
    Returns:
        str: 추출된 텍스트
    """
    try:
        pdf_file = io.BytesIO(pdf_data)
        pdf_reader = PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
        
    except Exception as e:
        raise Exception(f"PDF 텍스트 추출 실패: {str(e)}")


def extract_tech_stacks_with_ollama(resume_text, ollama_url=None):
    """
    Ollama Gemma3:12b 모델을 사용하여 이력서에서 기술 스택 추출
    
    Args:
        resume_text (str): 이력서 텍스트
        ollama_url (str): Ollama 서버 URL (None이면 환경변수 OLLAMA_URL 사용)
        
    Returns:
        list: 추출된 기술 스택 이름 리스트
    """
    # 환경변수에서 Ollama URL 가져오기
    if ollama_url is None:
        ollama_url = config('OLLAMA_URL', default='http://localhost:11434')
    try:
        # 데이터베이스에 있는 모든 기술 스택 목록 가져오기
        all_tech_stacks = list(TechStack.objects.values_list('name', flat=True))
        tech_stack_list = ", ".join(all_tech_stacks[:100])  # 처음 100개만 프롬프트에 포함
        
        # Ollama API 프롬프트 작성
        prompt = f"""
다음 이력서에서 사용된 기술 스택을 추출해주세요.

**이력서 내용:**
{resume_text[:3000]}  

**추출 규칙:**
1. 프로그래밍 언어, 프레임워크, 라이브러리, 도구, 플랫폼 등을 모두 포함
2. 다음 기술 스택 목록에서 찾아서 정확한 이름으로 추출: {tech_stack_list}
3. 결과는 JSON 배열 형식으로만 반환: ["Python", "Django", "React"]
4. 설명 없이 JSON만 반환

**JSON 형식 예시:**
["Python", "Django", "PostgreSQL", "React"]
"""
        
        # Ollama API 호출
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "gemma3:12b",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API 호출 실패: {response.status_code} - {response.text}")
        
        result = response.json()
        generated_text = result.get('response', '')
        
        # JSON 파싱
        try:
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            if '```json' in generated_text:
                generated_text = generated_text.split('```json')[1].split('```')[0].strip()
            elif '```' in generated_text:
                generated_text = generated_text.split('```')[1].split('```')[0].strip()
            
            tech_stacks = json.loads(generated_text)
            
            # 리스트가 아니면 빈 리스트 반환
            if not isinstance(tech_stacks, list):
                return []
            
            # 데이터베이스에 있는 기술 스택만 필터링
            valid_tech_stacks = []
            for tech in tech_stacks:
                if TechStack.objects.filter(name__iexact=tech).exists():
                    valid_tech_stacks.append(tech)
            
            return valid_tech_stacks
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 기술 스택 이름 추출 시도
            extracted = []
            for tech in all_tech_stacks:
                if tech.lower() in generated_text.lower():
                    extracted.append(tech)
            return extracted[:20]  # 최대 20개까지
        
    except Exception as e:
        raise Exception(f"Ollama 기술 스택 추출 실패: {str(e)}")


def analyze_resume(s3_url, ollama_url=None):
    """
    S3 URL에서 PDF를 다운로드하고, 텍스트를 추출한 후, Ollama로 기술 스택 분석
    
    Args:
        s3_url (str): S3 PDF URL
        ollama_url (str): Ollama 서버 URL (None이면 환경변수 OLLAMA_URL 사용)
        
    Returns:
        tuple: (텍스트, 기술 스택 리스트)
    """
    # 환경변수에서 Ollama URL 가져오기
    if ollama_url is None:
        ollama_url = config('OLLAMA_URL', default='http://localhost:11434')
    # 1. S3에서 PDF 다운로드
    pdf_data = download_pdf_from_s3(s3_url)
    
    # 2. PDF에서 텍스트 추출
    text = extract_text_from_pdf(pdf_data)
    
    # 3. Ollama로 기술 스택 추출
    tech_stacks = extract_tech_stacks_with_ollama(text, ollama_url)
    
    return text, tech_stacks
