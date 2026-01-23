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

## 빠른 시작

### 개발환경 실행

```bash
# 1. 전체 서비스 실행
docker compose -f docker-compose.dev.yml up -d

# 2. 실행 상태 확인
docker compose -f docker-compose.dev.yml ps

# 3. 로그 확인
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

## 문제 해결
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
