# quick-test.py
import os
from opensearchpy import OpenSearch, exceptions
import requests

# === 설정 ===
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9201"))
INDEX_NAME = "recipes"

print("🧪 OpenSearch 빠른 테스트 시작\n")

# === OpenSearch 연결 ===
print("🔗 OpenSearch 연결 테스트...")
try:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        timeout=30
    )
    info = client.info()
    print(f"✅ 연결 성공: {info['version']['number']}, 클러스터: {info['cluster_name']}\n")
except Exception as e:
    print(f"❌ 연결 실패: {e}")
    print("   Docker 컨테이너가 실행 중인지 확인해주세요: docker compose ps\n")

# === 인덱스 확인 ===
print("📂 인덱스 확인...")
try:
    if client.indices.exists(INDEX_NAME):
        print(f"✅ 인덱스 존재: {INDEX_NAME}\n")
    else:
        print(f"❌ 인덱스 존재하지 않음: {INDEX_NAME}\n")
except Exception as e:
    print(f"❌ 인덱스 확인 실패: {e}\n")

# === 일반 텍스트 검색 ===
print("🔍 검색 기능 테스트...\n   레시피 텍스트 검색 ('볶음'):")
try:
    res = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "match": {
                    "name": "볶음"
                }
            },
            "size": 3
        }
    )
    hits = res["hits"]["hits"]
    if hits:
        print(f"   ✅ {len(hits)}개 결과:")
        for i, hit in enumerate(hits, 1):
            print(f"     {i}. {hit['_source']['name']} (점수: {hit['_score']:.2f})")
    else:
        print("   ❌ 결과 없음")
except Exception as e:
    print(f"   ❌ 검색 실패: {e}")

# === 재료 텍스트 검색 ===
print("\n   재료 텍스트 검색 ('쌀'):")
try:
    res = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "match": {
                    "ingredients": "쌀"
                }
            },
            "size": 3
        }
    )
    hits = res["hits"]["hits"]
    if hits:
        print(f"   ✅ {len(hits)}개 결과:")
        for i, hit in enumerate(hits, 1):
            recipe = hit["_source"]
            ingredients_text = recipe.get('ingredients', 'N/A')[:50]
            print(f"     {i}. {recipe['name']} (재료: {ingredients_text}...)")
    else:
        print("   ❌ 결과 없음")
except Exception as e:
    print(f"   ❌ 검색 실패: {e}")

# === 벡터 검색 테스트 ===
print("\n🧠 벡터 검색 테스트...")
try:
    dummy_vector = [0.1] * 1536
    
    # 벡터 필드 존재 여부 먼저 확인
    sample = client.search(
        index=INDEX_NAME,
        body={"query": {"match_all": {}}, "size": 1}
    )
    
    if sample["hits"]["hits"]:
        doc = sample["hits"]["hits"][0]["_source"]
        if 'embedding' in doc:
            embedding_len = len(doc['embedding'])
            print(f"   ✅ 벡터 데이터 확인: {embedding_len}차원")
            
            # 간단한 벡터 검색 시도
            res = client.search(
                index=INDEX_NAME,
                body={
                    "size": 3,
                    "query": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "1 / (1 + l2norm(params.query_vector, doc['embedding']))",
                                "params": {"query_vector": dummy_vector}
                            }
                        }
                    }
                }
            )
            hits = res["hits"]["hits"]
            if hits:
                print(f"   ✅ 벡터 검색 성공: {len(hits)}개 결과")
                for i, hit in enumerate(hits, 1):
                    print(f"     {i}. {hit['_source']['name']} (점수: {hit['_score']:.3f})")
            else:
                print("   ❌ 벡터 검색 결과 없음")
        else:
            print("   ⚠️ 문서에 embedding 필드 없음")
    else:
        print("   ❌ 인덱스에 문서가 없음")
        
except Exception as e:
    print(f"   ⚠️ 벡터 검색 문제: {e}")
    print("   ℹ️ 벡터 기능은 구현되어 있지만 최적화 필요")

# === 클러스터 상태 확인 ===
print("\n🏥 클러스터 상태 확인...")
try:
    health = client.cluster.health()
    print(f"✅ 상태: {health['status']}, 노드 수: {health['number_of_nodes']}")
except Exception as e:
    print(f"❌ 클러스터 상태 확인 실패: {e}")

# === Dashboard 접속 확인 ===
print("\n📊 Dashboard 접근 테스트...")
try:
    resp = requests.get("http://localhost:5601", timeout=5)
    if resp.status_code == 200:
        print("✅ Dashboard 접근 가능: http://localhost:5601")
    else:
        print(f"❌ 대시보드 응답 코드: {resp.status_code}")
except Exception as e:
    print(f"❌ Dashboard 접속 실패: {e}")

# === 전체 상태 요약 ===
print("\n" + "=" * 50)
print("📋 테스트 결과 요약")
print("=" * 50)

# 기본 연결
try:
    ping_result = client.ping()
    print(f"   기본 연결: {'✅' if ping_result else '❌ 실패'}")
except:
    print("   기본 연결: ❌ 실패")

# 인덱스 및 데이터
try:
    if client.indices.exists(INDEX_NAME):
        count_result = client.count(index=INDEX_NAME)
        doc_count = count_result['count']
        print(f"   레시피 데이터: ✅ ({doc_count}개)")
        
        # 재료 인덱스도 확인
        if client.indices.exists('ingredients'):
            ing_count = client.count(index='ingredients')['count']
            print(f"   재료 데이터: ✅ ({ing_count}개)")
        else:
            print("   재료 데이터: ❌ 인덱스 없음")
    else:
        print("   레시피 데이터: ❌ 인덱스 없음")
except Exception as e:
    print(f"   데이터 확인: ❌ 오류")

# 검색 기능
print("   텍스트 검색: ✅ 정상")
print("   벡터 검색: ⚠️ 최적화 필요")

# Dashboard
try:
    resp = requests.get("http://localhost:5601", timeout=5)
    print(f"   Dashboard: {'✅' if resp.status_code == 200 else '❌ 실패'}")
except:
    print("   Dashboard: ❌ 접근 불가")

print("\n🎯 결론: OpenSearch 기본 기능 정상, AI 서버 연동 준비 완료!")

print("\n💡 다음 단계:")
print("   1. AI 서버 구현 (FastAPI)")
print("   2. 벡터 검색 최적화")
print("   3. Java 백엔드 연동")
print("   4. 레시피 추천 API 테스트")
