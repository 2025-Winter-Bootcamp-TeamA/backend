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

## 환경변수 설정

### 1. .env 파일 생성

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env
```

### 2. .env 파일 수정

`.env` 파일을 열어 실제 값을 입력하세요.

**필수 환경변수:**
| 변수명 | 설명 |
|--------|------|
| `SECRET_KEY` | Django 시크릿 키 |
| `DB_PASSWORD` | PostgreSQL 비밀번호 |
| `RABBITMQ_PASSWORD` | RabbitMQ 비밀번호 |

**SECRET_KEY 생성 방법:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> `.env` 파일은 Git에 커밋되지 않습니다. 팀원 간 별도로 공유해야 합니다.

---

## Docker Compose 파일 비교

| 파일 | 용도 | 실행 명령어 |
|------|------|-------------|
| `docker-compose.dev.yml` | 개발환경 | `docker compose -f docker-compose.dev.yml up -d` |
| `docker-compose.yml` | 배포환경 | `docker compose up -d` |

### docker-compose.dev.yml (개발환경)

| 서비스 | 설명 | 포트 |
|--------|------|------|
| postgres | PostgreSQL | 127.0.0.1:5432 |
| redis | Redis | 127.0.0.1:6379 |
| rabbitmq | RabbitMQ | 127.0.0.1:5672, 15672 |
| backend | Django (runserver) | 127.0.0.1:8000 |
| celery | Celery Worker | - |
| celery-beat | Celery 스케줄러 | - |

**특징:**
- 모든 포트가 `127.0.0.1`로 바인딩 (로컬에서만 접근 가능)
- `runserver` 사용 (코드 변경 시 자동 재시작)
- 볼륨 마운트로 코드 실시간 반영

### docker-compose.yml (배포환경)

| 서비스 | 설명 |
|--------|------|
| postgres | PostgreSQL (내부 네트워크만) |
| redis | Redis (내부 네트워크만) |
| rabbitmq | RabbitMQ (내부 네트워크만) |
| backend | Django + Gunicorn |
| celery | Celery Worker |
| celery-beat | Celery 스케줄러 |
| nginx | 리버스 프록시 (80, 443) |

**특징:**
- Nginx를 통해서만 외부 접근 가능
- `gunicorn` 사용 (멀티 워커)
- `restart: always` 설정

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
├── docker-compose.yml          # 배포용 Docker Compose
├── docker-compose.dev.yml      # 개발용 Docker Compose
├── Dockerfile                  # Docker 이미지 빌드
├── requirements.txt            # Python 패키지
├── manage.py                   # Django CLI
├── .env.example                # 환경변수 템플릿
└── .env                        # 환경변수 (Git 제외)
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

# 데이터베이스 접속
docker compose -f docker-compose.dev.yml exec postgres psql -U teamA -d teamAdb

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
