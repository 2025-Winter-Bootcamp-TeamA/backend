import os
from .pdf_text_extractor import extract_text_from_pdf, extract_text_from_pdf_url
from .tech_stack_extractor import get_tech_stacks_from_text

def analyze_pdf_for_tech_stacks(pdf_source: str, is_url: bool = False):
    """
    PDF 파일 또는 URL에서 텍스트를 추출하고 기술 스택을 분석합니다.

    :param pdf_source: PDF 파일 경로 또는 URL
    :param is_url: pdf_source가 URL인지 여부 (True면 URL, False면 로컬 경로)
    :return: 추출된 기술 스택 목록 또는 오류 메시지
    """
    print(f"--- PDF 분석 시작: {pdf_source} ---")
    try:
        if is_url:
            print("URL에서 텍스트 추출 중...")
            extracted_text = extract_text_from_pdf_url(pdf_source)
        else:
            print("로컬 파일에서 텍스트 추출 중...")
            extracted_text = extract_text_from_pdf(pdf_source)
        
        print(f"텍스트 추출 완료. 총 {len(extracted_text)}자.")

        if not extracted_text.strip():
            return "오류: 텍스트를 추출했지만 내용이 비어있습니다. (추출 실패 또는 빈 문서)"

        print("추출된 텍스트에서 기술 스택 분석 중...")
        tech_stacks = get_tech_stacks_from_text(extracted_text)
        
        return tech_stacks

    except FileNotFoundError as e:
        return f"오류: 파일을 찾을 수 없습니다 - {e}"
    except ValueError as e:
        return f"오류: 유효하지 않은 입력 - {e}"
    except Exception as e:
        return f"오류 발생: {e}"

def run_analysis_and_print_results(title: str, result):
    """분석 결과를 형식에 맞게 출력하는 헬퍼 함수"""
    print(f"\n=== {title} ===")
    if isinstance(result, list):
        if not result:
            print("분석 결과: 추출된 기술 스택이 없습니다.")
        else:
            for stack in result:
                print(f"- {stack}")
    else:
        # 오류 메시지 출력
        print(result)
    print("=" * (len(title) + 4))
    print("\n" + "-"*80 + "\n")


if __name__ == "__main__":
    # --- 시나리오 1: 로컬 PDF 파일 분석 ---
    # !!! 중요: 아래 경로를 실제 존재하는 PDF 파일 경로로 수정해주세요. !!!
    local_pdf_path = "/Users/psc/Downloads/기술 스택 추출 프롬프트 개선.pdf"
    
    if os.path.exists(local_pdf_path):
        result_local = analyze_pdf_for_tech_stacks(local_pdf_path, is_url=False)
        run_analysis_and_print_results("로컬 PDF 분석 결과", result_local)
    else:
        print(f"[경고] 로컬 PDF 파일 '{local_pdf_path}'을(를) 찾을 수 없습니다. 로컬 파일 분석을 건너뜁니다.")
        print("정확한 PDF 파일 경로로 'local_pdf_path' 변수를 수정해주세요.\n")


    url_pdf_path = "" 

    if url_pdf_path:
        result_url = analyze_pdf_for_tech_stacks(url_pdf_path, is_url=True)
        run_analysis_and_print_results("URL PDF 분석 결과", result_url)
    else:
        print("[경고] URL이 설정되지 않아 URL PDF 분석을 건너뜁니다.")
        print("유효한 PDF URL로 'url_pdf_path' 변수를 수정해주세요.\n")

    
    # --- 시나리오 3: 일반 텍스트 직접 분석 ---
    plain_text_to_analyze = """
    ## 주요 경험
    - Python, Django, FastAPI를 사용하여 RESTful API를 개발했습니다.
    - 데이터베이스는 PostgreSQL과 MySQL을 사용했으며, SQLAlchemy와 같은 ORM에 익숙합니다.
    - 프론트엔드 개발 시 React, Vue.js 프레임워크와 협업한 경험이 있습니다.
    - 인프라 환경으로 AWS를 사용했으며, 특히 EC2, S3, RDS를 주로 다루었습니다.
    - Git을 사용한 형상 관리에 익숙합니다.
    """
    
    print("--- 일반 텍스트 분석 시작 ---")
    try:
        result_plain = get_tech_stacks_from_text(plain_text_to_analyze)
        run_analysis_and_print_results("일반 텍스트 분석 결과", result_plain)
    except Exception as e:
        run_analysis_and_print_results("일반 텍스트 분석 결과", f"오류 발생: {e}")
