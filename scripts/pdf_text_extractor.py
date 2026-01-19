import PyPDF2
import os
import requests
import io
import re

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    로컬 PDF 파일에서 모든 텍스트를 추출하여 반환합니다.
    추출된 텍스트는 불필요한 줄바꿈과 공백이 제거되어 자연스러운 문장 흐름을 가집니다.

    :param pdf_path: 로컬 PDF 파일의 경로
    :return: 추출된 텍스트 전체 문자열
    :raises FileNotFoundError: 파일이 존재하지 않을 경우
    :raises PyPDF2.errors.PdfReadError: 유효한 PDF 파일이 아닐 경우
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"지정된 파일은 PDF 파일이 아닙니다: {pdf_path}")

    full_text = []
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    full_text.append(page_text)
        
        # 모든 페이지 텍스트를 결합하고 후처리 (여러 공백/줄바꿈을 하나의 공백으로 대체)
        processed_text = " ".join(full_text)
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        return processed_text
    except PyPDF2.errors.PdfReadError as e:
        raise PyPDF2.errors.PdfReadError(f"유효한 PDF 파일이 아닙니다: {pdf_path}. 오류: {e}")
    except Exception as e:
        print(f"PDF 텍스트 추출 중 예상치 못한 오류 발생: {e}")
        raise

def extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    URL로부터 PDF 파일을 다운로드하여 모든 텍스트를 추출합니다.
    추출된 텍스트는 불필요한 줄바꿈과 공백이 제거되어 자연스러운 문장 흐름을 가집니다.

    :param pdf_url: PDF 파일의 URL (예: S3 주소)
    :return: 추출된 텍스트 전체 문자열
    :raises requests.exceptions.RequestException: URL 요청 실패 시
    :raises PyPDF2.errors.PdfReadError: 유효한 PDF 파일이 아닐 경우
    """
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생

        # 메모리 상에서 PDF 파일을 처리하기 위해 BytesIO 사용
        pdf_file = io.BytesIO(response.content)

        full_text = []
        reader = PyPDF2.PdfReader(pdf_file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                full_text.append(page_text)
        
        # 모든 페이지 텍스트를 결합하고 후처리 (여러 공백/줄바꿈을 하나의 공백으로 대체)
        processed_text = " ".join(full_text)
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        return processed_text
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"URL에서 파일을 가져오는 데 실패했습니다: {pdf_url}. 오류: {e}")
    except PyPDF2.errors.PdfReadError as e:
        raise PyPDF2.errors.PdfReadError(f"URL에서 가져온 파일이 유효한 PDF가 아닙니다: {pdf_url}. 오류: {e}")
    except Exception as e:
        print(f"URL PDF 텍스트 추출 중 예상치 못한 오류 발생: {e}")
        raise

if __name__ == "__main__":
    # --- 1. 로컬 파일 테스트 ---
    # 테스트를 위한 예시 PDF 파일 경로 (실제 PDF 파일 경로로 변경 필요)
    sample_pdf_path = "" # 이 경로를 실제 테스트할 PDF 파일 경로로 수정하세요.

    if not os.path.exists(sample_pdf_path):
        print(f"\n[경고] 로컬 테스트를 위해 '{sample_pdf_path}' 파일을 찾을 수 없습니다.")
        print("실제 PDF 파일 경로를 'sample_pdf_path' 변수에 지정하여 다시 시도해주세요.")
    else:
        print(f"\n'{sample_pdf_path}' 파일에서 텍스트 추출 시도...")
        try:
            extracted_text = extract_text_from_pdf(sample_pdf_path)
            print("\n--- 로컬 파일 추출된 텍스트 ---")
            print(extracted_text)
            print("------------------------------")
        except Exception as e:
            print(f"오류: {e}")

    print("\n" + "="*50 + "\n")

    # --- 2. URL 테스트 ---
    # 테스트를 위한 예시 PDF URL (공개적으로 접근 가능한 PDF URL로 변경 필요)
    sample_pdf_url = "https://2025-winter-bootcamp-team-a-s3.s3.amazonaws.com/resumes/user_2/1_%EA%B8%B0%EC%88%A0%20%EC%8A%A4%ED%83%9D%20%EC%B6%94%EC%B6%9C%20%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8%20%EA%B0%9C%EC%84%A0.pdf" # 테스트할 PDF URL로 수정하세요.

    print(f"'{sample_pdf_url}' URL에서 텍스트 추출 시도...")
    try:
        extracted_text_url = extract_text_from_pdf_url(sample_pdf_url)
        print("\n--- URL 추출된 텍스트 (앞 500자) ---")
        print(extracted_text_url[:500]) # 전체 텍스트가 너무 길 수 있으므로 일부만 출력
        print("-----------------------------------")
    except Exception as e:
        print(f"오류: {e}")
