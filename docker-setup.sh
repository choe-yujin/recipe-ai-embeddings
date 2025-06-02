#!/bin/bash
echo "===================================="
echo "Recipe AI Project - Docker Setup"
echo "===================================="
echo

echo "🔍 Docker 상태 확인 중..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다"
    echo "   Docker Desktop을 설치하고 실행해주세요"
    exit 1
fi

echo "✅ Docker 설치 확인됨"

echo
echo "🐳 OpenSearch 컨테이너 시작 중..."
docker compose down > /dev/null 2>&1
docker compose up -d

echo
echo "⏳ OpenSearch 준비 대기 중 (최대 60초)..."
count=0
while [ $count -lt 12 ]; do
    if curl -s http://localhost:9201 > /dev/null 2>&1; then
        break
    fi
    
    count=$((count + 1))
    echo "   시도 $count/12..."
    sleep 5
done

if [ $count -ge 12 ]; then
    echo "❌ OpenSearch 준비 시간 초과"
    echo "   로그 확인: docker compose logs opensearch"
    exit 1
fi

echo "✅ OpenSearch 준비 완료!"

# ... 기존 스크립트 ...
echo "✅ OpenSearch 준비 완료!"

echo
echo "🔧 k-NN 설정 적용 중..."
curl -X PUT "http://localhost:9201/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "persistent": {
      "knn.memory.circuit_breaker.enabled": true
    }
  }'
echo "✅ k-NN 설정 적용 완료"

echo
echo "🧪 빠른 연결 테스트..."
if curl -s http://localhost:9201 | grep -q "cluster_name"; then
    echo "✅ 연결 테스트 성공"
else
    echo "❌ 연결 테스트 실패"
fi

echo
echo "📊 상태 확인..."
if curl -s "http://localhost:9201/_cat/indices" | grep -q "recipes"; then
    echo "✅ 인덱스 확인됨"
else
    echo "⚠️ 인덱스가 없습니다. 임베딩 업로드가 필요합니다."
    echo "   실행: python scripts/upload_to_opensearch_local.py"
fi

echo
echo "===================================="
echo "🎉 설정 완료!"
echo "===================================="
echo
echo "📋 접속 정보:"
echo "   OpenSearch API: http://localhost:9201"
echo "   Dashboard: http://localhost:5601"
echo
echo "🧪 테스트 명령어:"
echo "   curl http://localhost:9201"
echo "   python scripts/quick-test.py"
echo
echo "🔧 관리 명령어:"
echo "   중지: docker compose down"
echo "   재시작: docker compose restart"
echo "   로그: docker compose logs opensearch"
echo
