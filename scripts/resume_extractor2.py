import ollama
import json
import re
from typing import Optional, Dict, Any

class ResumeParserSystem:
    def __init__(self, model: str = 'gemma3:12b'):
        self.model = model
        self.max_retries = 2 

    def _extract_pure_json(self, text: str) -> str:
        """텍스트에서 JSON 구조만 추출합니다."""
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        return match.group(0) if match else text

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """API 호출 및 JSON 파싱을 수행합니다."""
        content = ""
        try:
            response = ollama.chat(
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

    # def parse(self, resume_text: str) -> Optional[Dict[str, Any]]:
    #     feedback = None
    #     last_extracted = None
        
    #     for i in range(self.max_retries):
    #         print(f"\n--- [{i+1}/{self.max_retries}차 분석 및 검증 시도] ---")
    #         try:
    #             # 1. 추출 (기술명은 영어로, 설명은 한국어로 지시)
    #             print("1. 데이터 추출 중...", end=" ", flush=True)
    #             last_extracted = self._call_llm(self._get_extractor_prompt(resume_text, feedback))
    #             print("완료")

    #             # 2. 검증 (언어 규칙 준수 여부 집중 체크)
    #             print("2. 데이터 검증 중...", end=" ", flush=True)
    #             verification = self._call_llm(self._get_verifier_prompt(resume_text, last_extracted))
                
    #             if verification.get('is_valid'):
    #                 print("✅ 검증 통과!")
    #                 return last_extracted
    #             else:
    #                 feedback = verification.get('feedback')
    #                 print(f"⚠️ 검증 실패: {feedback}")
    #         except Exception as e:
    #             print(f"❌ 오류 발생: {e}")
    #             continue
        
    #     print("\n🚨 최대 재시도를 초과했습니다. 최종 추출 데이터를 반환합니다.")
    #     return last_extracted
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

# --- 실행부 ---
if __name__ == "__main__":
    parser = ResumeParserSystem()
    sample_text = """
[경력 사항 (Professional History)]

1. 글로벌 AI 솔루션즈 (2022.02 - 현재)

직책: 시니어 데이터 사이언티스트

핵심 과업:

초개인화 추천 엔진 고도화: 유저의 실시간 클릭 로그를 분석하여 PyTorch 기반의 협업 필터링 모델을 설계. CTR(클릭률)을 기존 대비 22% 향상시킴.

수요 예측 모델 최적화: XGBoost와 LightGBM을 활용한 재고 수요 예측 시스템 구축으로 물류 폐기 비용을 연간 15% 절감.

데이터 파이프라인 자동화: Airflow를 도입하여 원천 데이터 수집부터 모델 서빙까지의 전 과정을 자동화하여 데이터 가공 시간을 주당 20시간 단축.

2. 데이터인사이트 랩 (2019.06 - 2021.12)

포지션: 데이터 분석가

주요 기여:

이커머스 유저 이탈 방지 분석: Python과 SQL을 이용해 이탈 징후 코호트를 정의하고, 타겟 마케팅을 제안하여 이탈률 10% 감소에 기여.

A/B 테스트 설계 및 검증: 신규 UI 배포 전 통계적 유의성 검정을 수행하여 의사결정 속도와 정확도를 개선.

시각화 대시보드 구축: Tableau를 활용해 전사 핵심 지표(KPI) 모니터링 시스템을 구축하여 보고 프로세스 효율화.

[수행 프로젝트 (Key Projects)]

1. 한국어 거대언어모델(LLM) 파인튜닝 (2024.01 - 2024.05)

배경: 사내 지식 베이스 기반의 전문 상담 챗봇 구축

활용 기술: Hugging Face, LangChain, Vector DB (Pinecone)

수행 상세: RAG(Retrieval-Augmented Generation) 패턴을 적용하여 답변 정확도를 90% 이상 확보하고, 내부 지식 검색 시간을 70% 단축.

2. 실시간 이상 탐지 시스템 (대학원 산학 협력)

배경: 공정 라인 센서 데이터를 활용한 불량품 사전 탐지

사용 도구: Scikit-learn, Pandas, Matplotlib

성과: Isolation Forest 알고리즘을 적용하여 기존 룰 기반 시스템보다 탐지 정확도를 18% 개선.

[학력 및 자격 (Background)]

미래공과대학교 대학원 (2017.03 - 2019.02): 데이터사이언스 전공 (석사 졸업)

Google Data Analytics Professional Certificate (2021.05 취득)

[보유 역량 (Capabilities)]

기술 도구: Python, SQL, R, PyTorch, TensorFlow, Scikit-learn, Airflow, Spark, Tableau

방법론: Machine Learning, Deep Learning, Statistics, A/B Testing, MLOps

기타: 국내외 데이터 분석 경진대회(Kaggle) 상위 5% 입상, '데이터 읽기' 관련 외부 강연 5회 진행
"""
    
    final_result = parser.parse(sample_text)
    if final_result:
        print("\n" + "="*50)
        print("[최종 구조화 데이터]")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))
        print("="*50)