#사용방법 루트 디렉토리에서 python -m scripts.resume_extractor_with_pdf "PDF_파일_URL" 실행
import argparse
import json
import os
from scripts.pdf_text_extractor import extract_text_from_pdf, extract_text_from_pdf_url
from scripts.module_resume_extractor import ResumeParserSystem

def main():
    """
    PDF 파일 경로 또는 URL을 인자로 받아 이력서 내용을 추출하고 구조화된 JSON으로 분석합니다.
    """
    # 1. 커맨드 라인에서 PDF 경로 또는 URL을 받습니다.
    parser = argparse.ArgumentParser(description="PDF 이력서를 분석하여 JSON으로 변환합니다.")
    parser.add_argument("source", help="분석할 PDF 파일의 로컬 경로 또는 URL")
    args = parser.parse_args()

    resume_text = None
    try:
        # 2. 입력이 URL인지 로컬 파일인지 확인하고 텍스트를 추출합니다.
        if args.source.startswith("http://") or args.source.startswith("https://"):
            print(f"URL에서 텍스트 추출 중: {args.source}")
            resume_text = extract_text_from_pdf_url(args.source)
        else:
            print(f"로컬 파일에서 텍스트 추출 중: {args.source}")
            resume_text = extract_text_from_pdf(args.source)
    except Exception as e:
        print(f"오류: 텍스트 추출에 실패했습니다. {e}")
        return

    # 3. 추출된 텍스트가 있으면 파싱을 시도합니다.
    if resume_text and resume_text.strip():
        print("텍스트 추출 완료. 이제 LLM으로 분석을 시작합니다...")
        
        # Docker 환경인지 감지하여 Ollama 호스트를 설정합니다.
        # Docker 안에서 실행하면 'host.docker.internal'을 사용해 호스트 머신의 Ollama에 접속합니다.
        ollama_host = 'http://host.docker.internal:11434' if os.path.exists('/.dockerenv') else None
        
        parser = ResumeParserSystem(host=ollama_host)
        structured_data = parser.parse(resume_text)

        # 4. 최종 결과를 출력합니다.
        if structured_data:
            print("\n--- 최종 분석 결과 ---")
            print(json.dumps(structured_data, indent=2, ensure_ascii=False))
            print("--- 분석 완료 ---")
        else:
            print("오류: 텍스트를 구조화하는 데 실패했습니다.")
    else:
        print("오류: PDF에서 텍스트를 추출할 수 없었습니다.")

if __name__ == "__main__":
    main()