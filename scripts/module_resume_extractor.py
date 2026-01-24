import ollama
import json
import re
from typing import Optional, Dict, Any

class ResumeParserSystem:
    def __init__(self, model: str = 'gemma3:4b', host: Optional[str] = None):
        self.model = model
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
                options={'temperature': 0, 'num_ctx': 16384, 'format': 'json'}
            )
            content = response['message']['content'].strip()
            json_str = self._extract_pure_json(content)
            return json.loads(json_str, strict=False)
        except Exception as e:
            print(f"\n   [!] JSON 처리 오류: {e}")
            raise e

    def _get_extractor_prompt(self, resume_text: str) -> str:
        return f"""
### Role: 구조화 데이터 분석가
### Instructions:
1. **언어 원칙**: 
   - **기술 스택 및 도구**(tools, technical_tools)는 반드시 **영문 공식 명칭**으로 작성하세요. (예: 파이썬 -> Python, 깃 -> Git)
   - **그 외 모든 설명**(details, context, organization 등)은 반드시 **원문 언어(한국어)**를 유지하세요. 영어로 번역하지 마세요.
   - **중복 방지**같은 내용을 반복하지 마세요. 또한, 직무 경험에 가깝다면 직무 경험에만 포함시키고 프로젝트 경험에 중복해서 포함시키지 마세요.
   - **문장 처리**기본적으로 이력서 내의 문장을 그대로 사용하되 맥락에 맞게 기존의 내용을 바꾸지 않는 선에서 약간의 수정을 가할 수 있습니다.
2. **무손실 원칙**: 원문에 등장하는 모든 사실적 파편을 상세히 리스트화하세요. 직무 경험, 프로젝트 경험은 빠뜨리지 마세요.
   - 정보가 너무 적은 프로젝트나 직무 경험에 대해서는 무시해도 좋습니다. 단, 기술 명칭은 한번이라도 포함되었다면 반드시 기록하세요.
3. **무결성**: 정보가 없으면 반드시 `null`을 반환하세요. 절대 정보를 추측하지 마세요.

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

    def parse(self, resume_text: str) -> Optional[Dict[str, Any]]:
        print("--- [데이터 추출 시작] ---")
        extracted_data = self._call_llm(self._get_extractor_prompt(resume_text))
        print("✅ 데이터 추출 완료.")
        return extracted_data

