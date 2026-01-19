import ollama
import json
import re
import os

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
            
            # (B) 2순위: 부분 일치 및 유의어 매핑
            else:
                # 후보 단어가 포함된 리스트 항목들을 모두 찾은 뒤, '짧은 순'으로 정렬
                # (Azure를 찾았을 때 Azure DevOps보다 Azure가 먼저 걸리도록 함)
                possible_keys = [k for k in target_lower_map.keys() if clean_cand in k or k in clean_cand]
                possible_keys.sort(key=len) 
                
                for target_key in possible_keys:
                    original_name = target_lower_map[target_key]
                    
                    # [검증 로직] 
                    # 만약 리스트 명칭(Azure DevOps)이 후보(Azure)보다 길다면,
                    # 본문에 그 차이(DevOps)가 실제로 존재하는지 확인!
                    remaining_part = target_key.replace(clean_cand, "").strip()
                    
                    if not remaining_part: # 후보와 리스트가 사실상 같음
                        matched_original = original_name
                        break
                    elif any(word in text_lower for word in remaining_part.split()):
                        # 본문에 나머지 단어(예: DevOps)가 있을 때만 매칭
                        matched_original = original_name
                        break
                    elif clean_cand in target_key.split():
                        # 후보 단어(AWS)가 리스트 항목의 핵심 독립 단어라면 인정 (브랜드명 대응)
                        matched_original = original_name
                        break

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
        
# --- 실행부 ---
if __name__ == "__main__":
    # 환경 변수 로드 (선택 사항, .env 파일 사용 시)
    from dotenv import load_dotenv
    load_dotenv()
    
    # PostgreSQL DB에서 기술 스택 목록 가져오기
    my_tech_stack = []
    try:
        import psycopg
        
        db_name = os.getenv('POSTGRES_DB', 'teamA_db')
        db_user = os.getenv('POSTGRES_USER', 'teamA')
        db_password = os.getenv('POSTGRES_PASSWORD', '2025')
        db_host = os.getenv('POSTGRES_HOST', 'postgres') # Docker 환경에서는 'db' 또는 서비스 이름
        db_port = os.getenv('POSTGRES_PORT', '5432')
        
        conn_info = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}"
        
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cursor:
                # 실제 테이블명은 'tech_stack' 입니다.
                cursor.execute("SELECT name FROM tech_stack;") 
                                             
                results = cursor.fetchall()
                my_tech_stack = [row[0] for row in results]
                
                print(f"[알림] 데이터베이스에서 {len(my_tech_stack)}개의 기술 스택을 성공적으로 로드했습니다.")

    except ImportError:
        print("[오류] psycopg 라이브러리가 설치되지 않았습니다.")
        print("requirements.txt에 'psycopg[binary]'가 있는지 확인해주세요.")
    except psycopg.OperationalError as e:
        print(f"[오류] 데이터베이스 연결에 실패했습니다: {e}")
        print("DB가 실행 중인지, 연결 정보가 정확한지 확인해주세요.")
    except psycopg.Error as e:
        print(f"[오류] 데이터베이스 조회 중 오류가 발생했습니다: {e}")
        print("테이블명(apps_techstack)이 정확한지 확인해주세요.")
    
    # 만약 DB 로드에 실패하여 my_tech_stack이 비어있으면, 분석을 건너뜁니다.
    if not my_tech_stack:
        print("[경고] 기술 스택 목록이 비어있어 분석을 건너뜁니다.")
        result = []
    else:
        # 테스트 텍스트
        import_text = """

        """

        # 분석 실행
        result = final_perfect_extractor(import_text, my_tech_stack)

    print("\n" + "="*40)
    print(f"### 최종 추출 결과 (총 {len(result)}개) ###")
    for tech in result:
        print(f"- {tech}")
    print("="*40)