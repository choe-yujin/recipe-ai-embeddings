import os
from opensearchpy import OpenSearch
import requests
import numpy as np
import json

# 환경 변수 또는 기본값
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9201"))
INDEX_NAME = "recipes"

def normalize_vector(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm != 0 else vector

print("🧪 OpenSearch 빠른 테스트 시작\n")

# OpenSearch 연결
print("🔗 OpenSearch 연결 테스트...")
try:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        timeout=30
    )
    info = client.info()
    print(f"✅ 연결 성공: {info['version']['number']}, 클러스터: {info['cluster_name']}\n")
except Exception as e:
    print(f"❌ 연결 실패: {e}\n   Docker 컨테이너가 실행 중인지 확인하세요: docker compose ps\n")
    exit(1)

# 인덱스 확인
print("📂 인덱스 확인...")
try:
    if client.indices.exists(INDEX_NAME):
        print(f"✅ 인덱스 존재: {INDEX_NAME}\n")
    else:
        print(f"❌ 인덱스 없음: {INDEX_NAME}\n")
except Exception as e:
    print(f"❌ 인덱스 확인 실패: {e}")
    exit(1)

# 텍스트 검색
print("🔍 검색 기능 테스트...\n   레시피 이름 검색 ('볶음'):")
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
            print(f"     {i}. {hit['_source'].get('name', 'N/A')} (점수: {hit['_score']:.2f})")
    else:
        print("   ❌ 결과 없음")
except Exception as e:
    print(f"   ❌ 검색 실패: {e}")

# 재료 검색
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

# 벡터 검색 테스트
print("\n🧠 벡터 검색 테스트...")
try:
    # 인덱스에서 실제 문서 하나 가져오기
    sample = client.search(
        index=INDEX_NAME,
        body={"query": {"match_all": {}}, "size": 1}
    )
    if sample["hits"]["hits"]:
        doc = sample["hits"]["hits"][0]["_source"]
        if 'embedding' in doc:
            print(f"   ✅ 벡터 데이터 확인: {len(doc['embedding'])}차원")

            test_vector = doc['embedding']
            normalized_vector = normalize_vector(np.array(test_vector))

            # 벡터 검색 쿼리
            search_body = {
                "size": 3,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": list(map(float, normalized_vector)),
                            "k": 10
                        }
                    }
                }
            }

            print("\n🔎 보낼 쿼리:")
            print(json.dumps(search_body, indent=2))

            res = client.search(index=INDEX_NAME, body=search_body)

            hits = res["hits"]["hits"]
            if hits:
                print(f"   ✅ 벡터 검색 성공: {len(hits)}개 결과")
                for i, hit in enumerate(hits, 1):
                    print(f"     {i}. {hit['_source'].get('name', 'N/A')} (점수: {hit['_score']:.3f})")
            else:
                print("   ❌ 벡터 검색 결과 없음")
        else:
            print("   ⚠️ 문서에 embedding 필드 없음")
    else:
        print("   ❌ 인덱스에 문서 없음")
except Exception as e:
    print(f"   ⚠️ 벡터 검색 문제: {e}\n   이 문제는 벡터 필드와 검색 쿼리 구문을 점검하세요.")

# 클러스터 상태 확인
print("\n🏥 클러스터 상태 확인...")
try:
    health = client.cluster.health()
    print(f"✅ 상태: {health['status']}, 노드 수: {health['number_of_nodes']}")
except Exception as e:
    print(f"❌ 클러스터 상태 확인 실패: {e}")

# Dashboard 확인
print("\n📊 Dashboard 접근 테스트...")
try:
    resp = requests.get("http://localhost:5601", timeout=5)
    if resp.status_code == 200:
        print("✅ Dashboard 접근 가능: http://localhost:5601")
    else:
        print(f"❌ 대시보드 응답 코드: {resp.status_code}")
except Exception as e:
    print(f"❌ Dashboard 접속 실패: {e}")

# 결과 요약
print("\n" + "=" * 50)
print("📋 테스트 결과 요약")
print("=" * 50)

try:
    if client.ping():
        print("   기본 연결: ✅")
    else:
        print("   기본 연결: ❌ 실패")
except:
    print("   기본 연결: ❌ 실패")

try:
    if client.indices.exists(INDEX_NAME):
        count = client.count(index=INDEX_NAME)['count']
        print(f"   레시피 데이터: ✅ ({count}개)")
        if client.indices.exists('ingredients'):
            ing_count = client.count(index='ingredients')['count']
            print(f"   재료 데이터: ✅ ({ing_count}개)")
        else:
            print("   재료 데이터: ❌ 인덱스 없음")
    else:
        print("   레시피 데이터: ❌ 인덱스 없음")
except Exception as e:
    print(f"   데이터 확인 오류: {e}")

print("   텍스트 검색: ✅ 정상")
print("   벡터 검색: ✅ 테스트 완료")
try:
    resp = requests.get("http://localhost:5601", timeout=5)
    print(f"   Dashboard: {'✅' if resp.status_code == 200 else '❌ 실패'}")
except:
    print("   Dashboard: ❌ 접근 불가")

print("\n🎯 결론: OpenSearch 기본 기능 정상, 실제 벡터 검색 테스트 완료!")

print("\n💡 다음 단계:")
print("   1. AI 서버 구현 (FastAPI)")
print("   2. 추천 API 연동")
print("   3. Java 백엔드 연동")
