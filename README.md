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

### Python 3.11 설치 (로컬 개발 시)

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
[Python 공식 사이트](https://www.python.org/downloads/)에서 3.11 버전 다운로드

**Linux (Ubuntu):**
```bash
sudo apt-get install python3.11 python3.11-venv python3-pip
```

---

## Docker Compose 파일 비교

### docker-compose.dev.yml (개발용 - 인프라만)

| 서비스 | 설명 |
|--------|------|
| db | PostgreSQL |
| redis | Redis |
| rabbitmq | RabbitMQ |

**특징:**
- 인프라 서비스만 포함 (DB, 캐시, 메시지 브로커)
- healthcheck 없음 (빠른 시작)
- Django, Celery, Nginx 없음

### docker-compose.yml (전체 서비스)

| 서비스 | 설명 |
|--------|------|
| db | PostgreSQL |
| redis | Redis |
| rabbitmq | RabbitMQ |
| backend | Django + Gunicorn |
| celery | Celery Worker |
| celery-beat | Celery 스케줄러 |
| nginx | 리버스 프록시 |

**특징:**
- 모든 서비스 포함
- healthcheck로 서비스 의존성 관리
- 프로덕션과 유사한 환경

### 언제 어떤 파일을 사용하나요?

| 파일 | 용도 | Django 실행 방식 |
|------|------|------------------|
| `docker-compose.dev.yml` | 로컬 개발 | `python manage.py runserver` (직접 실행) |
| `docker-compose.yml` | 통합 테스트/배포 | Docker 컨테이너 (Gunicorn) |

**docker-compose.dev.yml 사용 시점:**
- 코드 수정하면서 개발할 때
- 빠른 핫 리로드가 필요할 때
- 디버깅할 때

**docker-compose.yml 사용 시점:**
- 프로덕션 환경과 동일하게 테스트할 때
- 전체 시스템 통합 테스트할 때
- 다른 팀원에게 전체 환경을 공유할 때

---

## 빠른 시작 (Docker 사용)

### 1. 개발용 인프라 실행 (PostgreSQL, Redis, RabbitMQ)

```bash
# backend 디렉토리에서 실행
docker compose -f docker-compose.dev.yml up -d

# 실행 상태 확인
docker compose -f docker-compose.dev.yml ps

# 로그 확인
docker compose -f docker-compose.dev.yml logs -f
```

### 2. 전체 서비스 실행 (Backend + Gunicorn + Celery + Nginx)

```bash
# backend 디렉토리에서 실행
docker compose up -d --build

# 실행 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f backend
```

### 3. 서비스 접속

| 서비스 | URL |
|--------|-----|
| Backend API | http://localhost:8000/api/v1/ |
| API 문서 (Swagger) | http://localhost:8000/swagger/ |
| Django Admin | http://localhost:8000/admin/ |
| RabbitMQ 관리 콘솔 | http://localhost:15672 (teamA/2025) |

### 4. 서비스 중지

```bash
# 전체 서비스 중지
docker compose down

# 개발용 서비스 중지
docker compose -f docker-compose.dev.yml down

# 볼륨 포함 완전 삭제
docker compose down -v
```

---

## 로컬 개발 환경 (Docker 없이)

### 1. 가상환경 설정

```bash
# 가상환경 생성
python3.11 -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
.\venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

모든 환경변수(Backend + Frontend)는 `backend/.env`에서 통합 관리됩니다.
팀원에게 `.env` 파일을 직접 전달받아 `backend/` 폴더에 위치시키세요.

> ⚠️ `.env` 파일은 Git에 커밋되지 않습니다. 팀원 간 별도로 공유해야 합니다.

**주요 환경변수:**
| 변수명 | 설명 |
|--------|------|
| `SECRET_KEY` | Django 시크릿 키 |
| `DB_*` | PostgreSQL 접속 정보 |
| `REDIS_URL` | Redis 접속 URL |
| `CELERY_BROKER_URL` | RabbitMQ 접속 URL |
| `GOOGLE_API_KEY` | Google AI API 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `NEXT_PUBLIC_*` | Frontend 환경변수 |

### 4. 데이터베이스 설정

```bash
# Docker로 PostgreSQL만 실행
docker compose -f docker-compose.dev.yml up -d postgres

# 또는 개별 실행
docker run -d \
  --name postgres \
  -e POSTGRES_DB=teamAdb \
  -e POSTGRES_USER=teamA \
  -e POSTGRES_PASSWORD=2025 \
  -p 5432:5432 \
  postgres:15

# 마이그레이션
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

### 5. 서버 실행

```bash
python manage.py runserver
```

---

## Celery 실행

비동기 작업 처리를 위해 Celery를 실행합니다.

```bash
# Redis 실행
docker run -d --name redis -p 6379:6379 redis:7-alpine

# RabbitMQ 실행
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Celery Worker 실행
celery -A config worker -l info

# Celery Beat 실행 (스케줄러)
celery -A config beat -l info
```

---

## API 엔드포인트

| 경로 | 설명 |
|------|------|
| `/api/v1/users/` | 사용자 인증 및 프로필 |
| `/api/v1/trends/` | 기술 트렌드 |
| `/api/v1/jobs/` | 채용 공고 |
| `/api/v1/resumes/` | 이력서 관리 |
| `/api/v1/interviews/` | 면접 준비 |
| `/swagger/` | API 문서 (Swagger) |
| `/admin/` | 관리자 페이지 |

---

## 프로젝트 구조

```
backend/
├── apps/                       # Django 앱
│   ├── users/                  # 사용자 관리
│   ├── trends/                 # 기술 트렌드
│   ├── jobs/                   # 채용 공고
│   ├── resumes/                # 이력서
│   └── interviews/             # 면접 준비
├── config/                     # 설정
│   ├── settings/               # 환경별 설정
│   │   ├── base.py             # 공통 설정
│   │   ├── local.py            # 로컬 개발
│   │   └── production.py       # 프로덕션
│   ├── urls.py                 # URL 라우팅
│   ├── wsgi.py                 # WSGI
│   ├── asgi.py                 # ASGI
│   └── celery.py               # Celery
├── nginx/                      # Nginx 설정
│   └── nginx.conf
├── docker-compose.yml          # 전체 서비스 Docker Compose
├── docker-compose.dev.yml      # 개발용 Docker Compose (DB만)
├── Dockerfile                  # Docker 이미지 빌드
├── requirements.txt            # Python 패키지
├── manage.py                   # Django CLI
└── .env                        # 환경변수 (Git 제외, 팀원 간 공유)
```

---

## 유용한 명령어

### Docker 관련

```bash
# 컨테이너 상태 확인
docker compose ps

# 특정 서비스 재시작
docker compose restart backend

# 컨테이너 내부 접속
docker compose exec backend bash

# 데이터베이스 접속
docker compose exec postgres psql -U teamA -d teamAdb
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
