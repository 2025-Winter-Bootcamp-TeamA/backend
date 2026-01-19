import ollama
import json
import re
import os
import psycopg
from dotenv import load_dotenv
from datetime import datetime

def final_perfect_extractor(text, master_list, model="gemma3:12b"):
    if isinstance(master_list[0], list):
        master_list = master_list[0]
    
    # 1. 마스터 리스트 정리
    target_lower_map = {t.lower().strip(): t for t in master_list}
    text_lower = text.lower()
    
    print(f"[상태] 1. 분석 시작 (대상: {len(master_list)}개)")

    # 2. Ollama 후보 추출
    prompt = f"""
        당신은 베테랑 IT 채용 담당자입니다. [텍스트]에서 후보자의 기술적 역량을 나타내는 키워드를 빠짐없이 추출하세요.

        [추출 기준]
        - 프로그래밍 언어, 프레임워크, 라이브러리, 데이터베이스, 인프라, 클라우드 서비스, DevOps, CI/CD 툴 도구 등 모든 기술 스택.
        - 플랫폼 및 서비스 명칭도 포함.
        - '자바' -> 'Java'와 같이 한국어는 표준 영어 명칭으로 정규화하세요.
        - 프로젝트 설명이나 기술 스택 목록에 명시된 단어를 우선적으로 추출하세요.

        [주의 사항]
        - 반드시 JSON 형식으로만 응답하세요.
        - 결과에 부연 설명이나 인사는 포함하지 마세요.

        [텍스트]:
        \"\"\"{text}\"\"\"

        응답 형식:
        {{
        "tech_stack": ["명칭1", "명칭2", ...]
        }}
    """

    try:
        # Ollama 클라이언트 초기화 (환경 변수 OLLAMA_HOST를 사용하거나 기본값 사용)
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434') # 기본 Ollama 주소
        client = ollama.Client(host=ollama_host)
        
        response = client.chat(model=model, messages=[{'role': 'user', 'content': prompt}], format='json', options={'temperature': 0})
        
        raw_content = response['message']['content']
        parsed_content = json.loads(raw_content)
        
        candidates = []
        if isinstance(parsed_content, dict):
            for value in parsed_content.values():
                if isinstance(value, list):
                    candidates.extend(value)
        elif isinstance(parsed_content, list):
            candidates = parsed_content

        print(f"[상태] 2. Ollama 후보: {candidates}")

        final_matches = []

        for cand in candidates:
            clean_cand = cand.lower().strip()
            if not clean_cand: continue
            
            # --- [개선된 하이브리드 매칭 로직] ---
            matched_original = None
            
            # (A) 1순위: 완전 일치 체크 (가장 먼저 수행)
            if clean_cand in target_lower_map:
                matched_original = target_lower_map[clean_cand]
            
            # (B) 2순위: 부분 일치 및 유의어 매핑 (개선된 로직)
            else:
                # 후보(clean_cand)가 독립된 단어로서 포함된 DB의 모든 기술명(key)을 찾음
                possible_keys = []
                for k in target_lower_map.keys():
                    if re.search(rf"\b{re.escape(clean_cand)}\b", k):
                        possible_keys.append(k)
                
                possible_keys.sort(key=len)

                # 가장 적합한 키를 찾음
                for key in possible_keys:
                    # 남는 부분(확장된 부분)이 원본 텍스트에 존재하는지 확인
                    remaining_part = re.sub(rf"\b{re.escape(clean_cand)}\b", "", key, count=1).strip()
                    remaining_words = [word for word in re.split(r'[\s.-]', remaining_part) if word]

                    # 남는 부분이 없거나(react -> react.js), 남는 단어가 원문에 모두 있으면
                    if not remaining_words or all(word.lower() in text_lower for word in remaining_words):
                        matched_original = target_lower_map[key]
                        break # 가장 짧고, 검증된 매칭을 찾았으므로 종료
                
                # 만약 위에서 검증된 매칭을 못찾았지만, 가능한 후보가 단 하나뿐이라면 (모호하지 않은 경우)
                if not matched_original and len(possible_keys) == 1:
                    matched_original = target_lower_map[possible_keys[0]]

            # (C) 3순위: 최종 검증 (오탐 방지)
            if matched_original:
                # 2글자 이하(ws, r 등) -> 반드시 독립된 단어로 본문에 존재해야 함
                if len(clean_cand) <= 2:
                    if re.search(rf"\b{re.escape(clean_cand)}\b", text_lower):
                        final_matches.append(matched_original)
                # 3글자 이상 -> 본문에 후보 단어나 매핑된 이름의 흔적이 있으면 통과
                else:
                    if clean_cand in text_lower or matched_original.lower() in text_lower:
                        final_matches.append(matched_original)

        return sorted(list(set(final_matches)))

    except Exception as e:
        print(f"[오류] {e}")
        return []

def get_tech_stacks_from_text(text, model="gemma3:12b"):
    """
    주어진 텍스트에서 기술 스택 목록을 추출하고, 그 과정을 로그로 남깁니다.

    :param text: 분석할 텍스트 (예: 이력서, 프로젝트 설명)
    :param model: Ollama에서 사용할 모델 이름
    :return: 추출된 기술 스택 이름의 리스트
    """
    load_dotenv()
    
    my_tech_stack = []
    try:
        db_name = os.getenv('POSTGRES_DB', 'teamA_db')
        db_user = os.getenv('POSTGRES_USER', 'teamA')
        db_password = os.getenv('POSTGRES_PASSWORD', '2025')
        db_host = os.getenv('POSTGRES_HOST', 'postgres') # Docker 환경에서는 'db' 또는 서비스 이름
        db_port = os.getenv('POSTGRES_PORT', '5432')
        
        conn_info = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}"
        
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM tech_stack;") 
                                             
                results = cursor.fetchall()
                my_tech_stack = [row[0] for row in results]
                
                print(f"[알림] 데이터베이스에서 {len(my_tech_stack)}개의 기술 스택을 성공적으로 로드했습니다.")

    except ImportError:
        print("[오류] psycopg 라이브러리가 설치되지 않았습니다.")
        print("requirements.txt에 'psycopg[binary]'가 있는지 확인해주세요.")
        return []
    except psycopg.OperationalError as e:
        print(f"[오류] 데이터베이스 연결에 실패했습니다: {e}")
        print("DB가 실행 중인지, 연결 정보가 정확한지 확인해주세요.")
        return []
    except psycopg.Error as e:
        print(f"[오류] 데이터베이스 조회 중 오류가 발생했습니다: {e}")
        return []
    
    if not my_tech_stack:
        print("[경고] 기술 스택 목록이 비어있어 분석을 건너뜁니다.")
        return []
    
    # 기술 스택 추출
    result = final_perfect_extractor(text, my_tech_stack, model)
    
    # 로깅
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "input_text": text.strip(),
        "extracted_stacks": result,
    }
    
    try:
        with open("tech_stack_extraction_log.jsonl", "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[경고] 로그 파일 작성 중 오류 발생: {e}")

    return result

# --- 실행부 ---
if __name__ == "__main__":
    # 테스트 텍스트
    import_text = """
    ## 프로젝트 경험
    - Django 및 Django REST Framework를 사용한 백엔드 API 서버 개발
    - 주요 기술: Python, DRF, Celery, Redis
    - 데이터베이스: PostgreSQL 사용, ORM으로 쿼리 최적화 경험
    - 프론트엔드(협업): React, Redux-saga
    - 배포: Docker, Nginx, uWSGI를 사용하여 AWS EC2에 배포
    - CI/CD: Jenkins를 이용한 자동 배포 파이프라인 구축
    - 사용 언어: Java, C++도 일부 사용 경험
    """

    # 분석 실행
    result = get_tech_stacks_from_text(import_text)

    print("\n" + "="*40)
    print(f"### 최종 추출 결과 (총 {len(result)}개) ###")
    for tech in result:
        print(f"- {tech}")
    print("="*40)