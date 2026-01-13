# TeamA Backend

Django REST Framework 기반 백엔드 서버입니다.

## 기술 스택

- Python 3.11
- Django 5.0
- Django REST Framework 3.14
- PostgreSQL 15
- Redis 7
- Celery 5.3
- RabbitMQ 3 (메시지 브로커)
- Gunicorn (WSGI 서버)
- Docker & Docker Compose
- Nginx

---

## 사전 요구사항

### Docker 설치

**macOS:**
```bash
brew install --cask docker
docker --version
docker compose version
```

**Windows:**
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 다운로드 및 설치
2. WSL2 백엔드 활성화 권장

**Linux (Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose-v2
sudo usermod -aG docker $USER
```

---

## 빠른 시작

### 개발환경 실행

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 실제 값 입력

# 2. 전체 서비스 실행
docker compose -f docker-compose.dev.yml up -d

# 3. 실행 상태 확인
docker compose -f docker-compose.dev.yml ps

# 4. 로그 확인
docker compose -f docker-compose.dev.yml logs -f backend
```

### 서비스 접속

| 서비스 | URL |
|--------|-----|
| Backend API | http://localhost:8000/api/v1/ |
| API 문서 (Swagger) | http://localhost:8000/swagger/ |
| Django Admin | http://localhost:8000/admin/ |
| RabbitMQ 관리 콘솔 | http://localhost:15672 |

### 서비스 중지

```bash
# 중지 (컨테이너 유지)
docker compose -f docker-compose.dev.yml stop

# 중지 + 삭제
docker compose -f docker-compose.dev.yml down

# 볼륨 포함 완전 삭제 (DB 데이터 삭제됨)
docker compose -f docker-compose.dev.yml down -v
```

---

## 로컬 개발 환경 (Docker 없이)

인프라만 Docker로 실행하고, Django는 로컬에서 실행하는 방법입니다.

### 1. 가상환경 설정

```bash
# 가상환경 생성
python3 -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
.\venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 인프라 실행

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis rabbitmq
```

### 4. Django 서버 실행

```bash
# 마이그레이션
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser

# 서버 실행
python manage.py runserver
```

### 5. Celery 실행 (선택)

```bash
# 새 터미널에서 Celery Worker 실행
celery -A config worker -l info

# 새 터미널에서 Celery Beat 실행
celery -A config beat -l info
```

---

## 유용한 명령어

### Docker 관련

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.dev.yml ps

# 특정 서비스 재시작
docker compose -f docker-compose.dev.yml restart backend

# 컨테이너 내부 접속
docker compose -f docker-compose.dev.yml exec backend bash

# 데이터베이스 접속 (환경변수 사용)
docker compose -f docker-compose.dev.yml exec postgres psql -U ${DB_USER} -d ${DB_NAME}

# 이미지 재빌드
docker compose -f docker-compose.dev.yml build --no-cache backend
```

### Django 관련

```bash
# Django 셸 실행
python manage.py shell

# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic
```

---

## 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov

# 특정 앱 테스트
pytest apps/users/
```

---

## 문제 해결

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :5432

# 해당 프로세스 종료
kill -9 <PID>
```

### 데이터베이스 초기화

```bash
# 볼륨 삭제 후 재시작
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### 컨테이너 로그 확인

```bash
# 특정 서비스 로그
docker compose -f docker-compose.dev.yml logs -f backend

# 최근 100줄만
docker compose -f docker-compose.dev.yml logs --tail=100 backend
```
