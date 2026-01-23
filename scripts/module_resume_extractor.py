import ollama
import json
import re
from typing import Optional, Dict, Any

class ResumeParserSystem:
    def __init__(self, model: str = 'gemma3:4b', host: Optional[str] = None):
        self.model = model
        self.max_retries = 2
        self.client = ollama.Client(host=host)

    def _extract_pure_json(self, text: str) -> str:
        """텍스트에서 JSON 구조만 추출합니다."""
        match = re.search(r'({.*}|\[.*\])', text, re.DOTALL)
        return match.group(0) if match else text

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """API 호출 및 JSON 파싱을 수행합니다."""
        content = ""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0, 'format': 'json'}
            )
            content = response['message']['content'].strip()
            json_str = self._extract_pure_json(content)
            return json.loads(json_str, strict=False)
        except Exception as e:
            print(f"\n   [!] JSON 처리 오류: {e}")
            raise e

    def _get_extractor_prompt(self, resume_text: str, feedback: Optional[str] = None) -> str:
        feedback_msg = f"\n\n[이전 시도 피드백 반영]: {feedback}" if feedback else ""
        return f"""
### Role: 구조화 데이터 분석가
### Instructions:
1. **언어 원칙**: 
   - **기술 스택 및 도구**(tools, technical_tools)는 반드시 **영문 공식 명칭**으로 작성하세요. (예: 파이썬 -> Python, 깃 -> Git)
   - **그 외 모든 설명**(details, context, organization 등)은 반드시 **원문 언어(한국어)**를 유지하세요. 영어로 번역하지 마세요.
2. **무손실 원칙**: 원문에 등장하는 모든 사실적 파편을 상세히 리스트화하세요. 자격증, 프로젝트 경험, 수상 내역 등을 빠뜨리지 마세요.
3. **무결성**: 정보가 없으면 반드시 `null`을 반환하세요. 절대 정보를 추측하지 마세요.
{feedback_msg}

### Input Text:
{resume_text}

### Output Schema:
{{
  "work_experience": [
    {{ "organization": "기관명", "role": "역할", "period": "기간", "details": [] }}
  ],
  "project_experience": [
    {{ "name": "활동명", "period": "기간", "context": "배경", "tools": [], "details": [] }}
  ],
  "educational_background": [
    {{ "institution": "기관명", "period": "기간", "subject": "전공", "details": [] }}
  ],
  "key_capabilities": {{ "technical_tools": [], "methodologies": [], "others": [] }}
}}
"""

    def _get_verifier_prompt(self, resume_text: str, extracted_json: Dict[str, Any]) -> str:
        return f"""
### Role: 데이터 무결성 및 언어 검증 전문가
### Tasks:
1. **내용 정합성**: 원문의 정보가 누락되었거나 없는 정보가 생성(환각)되었는지 확인하세요. 영문과 한국어로 이루어진 자격증, 수상 내역, 프로젝트 내역 등이 없는지 꼼꼼히 확인하세요.
2. **기술명 영문 확인**: 'tools'와 'technical_tools'의 명칭이 영문 공식 명칭으로 작성되었습니까? (예: '파이썬'이 있으면 false)
3. **설명문 언어 확인**: 기술 명칭 외의 설명(details, organization 등)이 영어로 번역되었습니까? **번역되었다면 false입니다.** 반드시 한국어를 유지해야 합니다.
- 주의: 정보가 없어 `null`로 표시된 것은 정상입니다.

### Data:
- 원문: {resume_text}
- 추출 JSON: {json.dumps(extracted_json, ensure_ascii=False)}

### Output Format:
{{ "is_valid": true/false, "feedback": "미흡 사항(특히 언어 혼용 문제) 기술" }}
"""

    def parse(self, resume_text: str) -> Optional[Dict[str, Any]]:
        feedback = None
        last_extracted = None
        
        for i in range(self.max_retries): # max_retries = 2
            is_last_attempt = (i == self.max_retries - 1)
            
            print(f"--- [{i+1}/{self.max_retries}차 시도] ---")
            last_extracted = self._call_llm(self._get_extractor_prompt(resume_text, feedback))
            
            # 마지막 시도라면 검증 API를 호출하지 않고 바로 반환하여 비용 절감
            if is_last_attempt:
                print("마지막 시도이므로 검증 없이 데이터를 반환합니다.")
                return last_extracted

            # 마지막 시도가 아닐 때만 검증을 수행하여 피드백 생성
            verification = self._call_llm(self._get_verifier_prompt(resume_text, last_extracted))
            
            if verification.get('is_valid'):
                print("✅ 1차 시도에서 검증 통과!")
                return last_extracted
            else:
                feedback = verification.get('feedback')
                print(f"⚠️ 1차 검증 실패, 피드백 생성 완료")
                
        return last_extracted
