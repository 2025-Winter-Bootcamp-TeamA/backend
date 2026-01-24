#!/bin/bash
echo "🛑 Docker 컨테이너 중지 및 삭제..."
docker-compose -f docker-compose.dev.yml down -v

echo "🧹 볼륨 삭제..."
docker volume rm bootcamp-teama_postgres_data 2>/dev/null || true

echo "🚀 Docker 재시작..."
docker-compose -f docker-compose.dev.yml up -d

echo "✅ 완료! 로그 확인:"
docker-compose -f docker-compose.dev.yml logs -f
