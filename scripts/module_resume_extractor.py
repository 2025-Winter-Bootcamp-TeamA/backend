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
        return f"""이력서를 분석하여 JSON으로 변환하세요.

# 핵심 규칙
1. 기술명: 영문 (Python, Django)
2. 설명: 한국어 원문 유지
3. 없으면: [] (null 금지)
4. details: 각 항목 50자 이내

# 직무 경험 (work_experience) - 매우 엄격
**다음 단어 중 하나라도 있어야만 포함:**
- "재직", "근무", "인턴십", "아르바이트", "파트타임", "정규직", "계약직"

**없으면 무조건 []**

# 프로젝트 경험 (project_experience) - 유연하게
**다음 중 하나라도 해당하면 프로젝트:**
- "프로젝트" 단어가 있음
- 기술을 사용해서 무언가를 만든 경험
- "개발", "구현", "제작", "설계" 등의 단어
- Description이 있고 기술 스택이 나열됨

**주의:**
- "Backend Developer", "Frontend Developer" 같은 표현만으로는 직무 경험이 아님
- "재직", "근무" 같은 명시적 단어 없으면 프로젝트로 분류
- tools: 기술명만 (Java, Spring Boot, MySQL)
- details: 구현 내용 (CRUD 기능 개발, API 서버 구축)

# 예시 1: 프로젝트만 있음
입력:
"Java Spring Boot 웹 서비스 Backend Developer | 2025.12-2026.01
Description: 기본적인 CRUD 기능을 갖춘 Spring Boot 기반 웹 애플리케이션 개발
Tech Stack: Java, Spring Boot, MySQL"

출력:
{{
  "work_experience": [],
  "project_experience": [
    {{
      "name": "Java Spring Boot 웹 서비스",
      "period": "2025.12-2026.01",
      "context": "기본적인 CRUD 기능을 갖춘 Spring Boot 기반 웹 애플리케이션",
      "tools": ["Java", "Spring Boot", "MySQL"],
      "details": ["CRUD 기능 개발", "웹 애플리케이션 개발"]
    }}
  ],
  "educational_background": [],
  "key_capabilities": {{
    "technical_tools": ["Java", "Spring Boot", "MySQL"],
    "methodologies": [],
    "others": []
  }}
}}

# 예시 2: 직무 경험 있음
입력:
"네이버 백엔드 개발자로 재직 (2023-2024)
- 검색 API 개발
- Redis 캐싱 적용"

출력:
{{
  "work_experience": [
    {{
      "organization": "네이버",
      "role": "백엔드 개발자",
      "period": "2023-2024",
      "details": ["검색 API 개발", "Redis 캐싱 적용"]
    }}
  ],
  "project_experience": []
}}

# 분석할 이력서
{resume_text}

# 출력
JSON만 반환. "재직"/"근무" 없으면 work_experience는 []로 하고 프로젝트로 분류하세요."""

    def _validate_and_clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """추출된 데이터를 검증하고 정제합니다."""
        invalid_strings = ['null', 'none', '없음', '-', 'n/a', '']

        def is_valid_string(s: str) -> bool:
            """유효한 문자열인지 확인"""
            if not s or not isinstance(s, str):
                return False
            return s.strip().lower() not in invalid_strings

        def clean_list(items: list) -> list:
            """리스트에서 유효하지 않은 항목 제거"""
            if not isinstance(items, list):
                return []
            return [item.strip() for item in items if isinstance(item, str) and is_valid_string(item)]

        def is_actual_work_experience(org: str, role: str, period: str, details: list) -> bool:
            """실제 직무 경험인지 검증 (프로젝트와 구분)"""
            # 직무 경험을 나타내는 키워드
            work_keywords = ['재직', '근무', '인턴', '아르바이트', '파트타임', '정규직', '계약직', '프리랜서']

            # 프로젝트를 나타내는 키워드 (이게 있으면 직무 경험이 아님)
            project_keywords = ['프로젝트', '과제', '개발', '구현', '제작', '설계', '클론', '토이']

            # organization, role, period를 합쳐서 검사
            combined_text = f"{org} {role} {period}".lower()

            # 프로젝트 키워드가 있으면 직무 경험이 아님
            for keyword in project_keywords:
                if keyword in combined_text:
                    print(f"   ⚠️  '{org}'는 프로젝트로 판단됨 (키워드: '{keyword}')")
                    return False

            # 직무 경험 키워드가 하나라도 있어야 함
            has_work_keyword = any(keyword in combined_text for keyword in work_keywords)

            if not has_work_keyword:
                print(f"   ⚠️  '{org}'는 직무 경험 키워드가 없어 제외됨")
                return False

            return True

        # work_experience 정제 (강화된 검증)
        if 'work_experience' in data:
            valid_work_exp = []
            for exp in data['work_experience']:
                if not isinstance(exp, dict):
                    continue
                org = exp.get('organization', '').strip()
                role = exp.get('role', '').strip()
                period = exp.get('period', '').strip()
                details = clean_list(exp.get('details', []))

                # 1차 검증: organization과 details가 유효한지
                if not is_valid_string(org) or len(details) == 0:
                    continue

                # 2차 검증: 실제 직무 경험인지 확인
                if is_actual_work_experience(org, role, period, details):
                    exp['organization'] = org
                    exp['role'] = role
                    exp['period'] = period
                    exp['details'] = details
                    valid_work_exp.append(exp)

            data['work_experience'] = valid_work_exp

        # project_experience 정제
        if 'project_experience' in data:
            valid_proj_exp = []
            for exp in data['project_experience']:
                if not isinstance(exp, dict):
                    continue
                name = exp.get('name', '').strip()
                details = clean_list(exp.get('details', []))
                tools = clean_list(exp.get('tools', []))

                # name과 (details 또는 tools) 중 하나라도 있으면 포함
                if is_valid_string(name) and (len(details) > 0 or len(tools) > 0):
                    exp['name'] = name
                    exp['period'] = exp.get('period', '').strip()
                    exp['context'] = exp.get('context', '').strip()
                    exp['tools'] = tools
                    exp['details'] = details
                    valid_proj_exp.append(exp)
                    print(f"   ✅ 프로젝트 '{name}' 포함: {len(details)}개 기능, {len(tools)}개 기술")
                elif is_valid_string(name):
                    print(f"   ❌ 프로젝트 '{name}' 제외: details와 tools가 모두 없음")
            data['project_experience'] = valid_proj_exp

        # key_capabilities 정제
        if 'key_capabilities' in data:
            caps = data['key_capabilities']
            if isinstance(caps, dict):
                caps['technical_tools'] = clean_list(caps.get('technical_tools', []))
                caps['methodologies'] = clean_list(caps.get('methodologies', []))
                caps['others'] = clean_list(caps.get('others', []))

        return data

    def parse(self, resume_text: str) -> Optional[Dict[str, Any]]:
        print("\n" + "="*60)
        print("📄 이력서 분석 시작")
        print("="*60)
        print(f"\n[입력된 이력서 텍스트 미리보기 (첫 500자)]")
        print(resume_text[:500])
        print("...\n")

        extracted_data = self._call_llm(self._get_extractor_prompt(resume_text))

        print("\n[원본 LLM 응답]")
        print(json.dumps(extracted_data, ensure_ascii=False, indent=2))

        # 데이터 검증 및 정제
        print("\n[검증 과정]")
        cleaned_data = self._validate_and_clean_data(extracted_data)

        print("\n[정제된 데이터]")
        print(f"✅ 직무 경험: {len(cleaned_data.get('work_experience', []))}개")
        print(f"✅ 프로젝트 경험: {len(cleaned_data.get('project_experience', []))}개")

        if cleaned_data.get('work_experience'):
            for exp in cleaned_data['work_experience']:
                print(f"   - {exp['organization']}: {len(exp['details'])}개 업무")

        if cleaned_data.get('project_experience'):
            for exp in cleaned_data['project_experience']:
                print(f"   - {exp['name']}: {len(exp['details'])}개 기능, {len(exp['tools'])}개 기술")

        if len(cleaned_data.get('work_experience', [])) == 0 and len(cleaned_data.get('project_experience', [])) == 0:
            print("\n⚠️  경고: 직무 경험과 프로젝트 경험이 모두 추출되지 않았습니다!")
            print("   원인: LLM이 추출하지 못했거나, 검증 단계에서 모두 걸러졌습니다.")

        print("="*60 + "\n")

        return cleaned_data
