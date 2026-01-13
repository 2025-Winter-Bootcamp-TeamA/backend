# Docker 환경 가이드

이 문서는 개발환경과 배포환경의 Docker 구성 차이점과 실행 방법을 설명합니다.

---

## 파일 구조

```
backend/
├── docker-compose.yml      # 배포환경용
├── docker-compose.dev.yml  # 개발환경용
├── Dockerfile              # Docker 이미지 빌드
├── .env                    # 환경변수 (개발용)
└── nginx/
    └── nginx.conf          # Nginx 설정
```

---

## 개발환경 vs 배포환경 비교

| 항목 | 개발환경 (dev) | 배포환경 (prod) |
|------|---------------|-----------------|
| 파일 | `docker-compose.dev.yml` | `docker-compose.yml` |
| Django 서버 | `runserver` (hot-reload) | `gunicorn` (멀티 워커) |
| DEBUG | True | False |
| 볼륨 마운트 | `.:/app` (코드 실시간 반영) | 없음 (이미지에 포함) |
| Nginx | 없음 | 필수 (리버스 프록시) |
| 포트 노출 | 모든 서비스 포트 노출 | Nginx 80/443만 노출 |
| 로그 레벨 | info | warning |
| 재시작 정책 | 없음 | `restart: always` |

---

## 개발환경 실행 방법

### 방법 1: 전체 Docker 실행 (권장)

모든 서비스를 Docker로 실행합니다.

```bash
# backend 디렉토리로 이동
cd backend

# 전체 서비스 실행
docker compose -f docker-compose.dev.yml up -d

# 실행 상태 확인
docker compose -f docker-compose.dev.yml ps

# 로그 확인
docker compose -f docker-compose.dev.yml logs -f backend

# 중지 (컨테이너 유지)
docker compose -f docker-compose.dev.yml stop

# 중지 + 삭제
docker compose -f docker-compose.dev.yml down
```

**실행되는 서비스:**
- postgres (5432)
- redis (6379)
- rabbitmq (5672, 15672)
- backend (8000)
- celery
- celery-beat

**접속 URL:**
- Django: http://localhost:8000
- Swagger API 문서: http://localhost:8000/swagger/
- RabbitMQ 관리 콘솔: http://localhost:15672 (.env 파일 참고)

---

### 방법 2: 인프라만 Docker + Django 로컬 실행

코드 변경이 더 빠르게 반영됩니다.

```bash
# 1. 인프라만 Docker로 실행
docker compose -f docker-compose.dev.yml up -d postgres redis rabbitmq

# 2. Python 가상환경 활성화
source venv/bin/activate  # Mac/Linux
# 또는
.\venv\Scripts\activate  # Windows

# 3. Django 서버 로컬 실행
python manage.py runserver

# 4. (선택) Celery 워커 로컬 실행
celery -A config worker -l info

# 5. (선택) Celery Beat 로컬 실행
celery -A config beat -l info
```

---

### 방법 3: 특정 서비스만 실행

```bash
# DB만 실행
docker compose -f docker-compose.dev.yml up -d postgres

# DB + Redis만 실행
docker compose -f docker-compose.dev.yml up -d postgres redis

# Celery 제외하고 실행
docker compose -f docker-compose.dev.yml up -d postgres redis rabbitmq backend
```

---

## 배포환경 실행 방법

```bash
# backend 디렉토리로 이동
cd backend

# 이미지 빌드 + 실행
docker compose up -d --build

# 또는 빌드와 실행 분리
docker compose build
docker compose up -d

# 실행 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f

# 무중단 재배포 (backend만 재빌드)
docker compose up -d --build --no-deps backend celery celery-beat

# 중지
docker compose down
```

**접속 URL:**
- 웹사이트: http://localhost (Nginx를 통해)
- HTTPS: https://localhost (SSL 설정 시)

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

# 로그 확인 (실시간)
docker compose -f docker-compose.dev.yml logs -f backend celery

# 이미지 재빌드
docker compose -f docker-compose.dev.yml build --no-cache backend
```

### Django 관련 (Docker 내부)

```bash
# 마이그레이션 생성
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations

# 마이그레이션 적용
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

# 슈퍼유저 생성
docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser

# Django 셸
docker compose -f docker-compose.dev.yml exec backend python manage.py shell
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
# 볼륨 삭제 (데이터 삭제됨!)
docker compose -f docker-compose.dev.yml down -v

# 다시 실행
docker compose -f docker-compose.dev.yml up -d
```

### 이미지 재빌드

```bash
# 캐시 없이 재빌드
docker compose -f docker-compose.dev.yml build --no-cache

# 실행
docker compose -f docker-compose.dev.yml up -d
```

### 컨테이너 로그 확인

```bash
# 모든 서비스 로그
docker compose -f docker-compose.dev.yml logs

# 특정 서비스 로그 (실시간)
docker compose -f docker-compose.dev.yml logs -f backend

# 최근 100줄만
docker compose -f docker-compose.dev.yml logs --tail=100 backend
```

---

## Docker Desktop 그룹화

두 파일 모두 `name: bootcamp-teamA`가 설정되어 있어,
Docker Desktop에서 **bootcamp-teamA** 그룹으로 컨테이너들이 표시됩니다.
