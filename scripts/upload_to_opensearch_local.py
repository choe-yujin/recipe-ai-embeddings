# ============================================================================
# Local OpenSearch 데이터 업로드 스크립트 (로컬 환경용)
# ============================================================================
# 목적: 1136개 레시피와 약 500개 재료의 벡터 임베딩을 로컬 OpenSearch에 업로드
# 사용법: python upload_to_opensearch_local.py
# 필수 환경변수: OPENSEARCH_HOST, OPENSEARCH_PORT
# ============================================================================

import json
import os
from opensearchpy import OpenSearch, helpers
from dotenv import load_dotenv
import time

# .env 파일에서 환경변수 로드
load_dotenv()

# ============================================================================
# OpenSearch 클라이언트 설정 (로컬용)
# ============================================================================

def create_opensearch_client():
    """로컬 OpenSearch 클라이언트를 생성합니다."""
    host = os.getenv('OPENSEARCH_HOST', 'localhost')
    port = int(os.getenv('OPENSEARCH_PORT', '9201'))
    
    print("[OpenSearch] 로컬 OpenSearch 접근")
    print(f"   - 호스트: {host}")
    print(f"   - 포트: {port}")
    return OpenSearch(
        hosts=[{'host': host, 'port': port}],
        use_ssl=False,
        verify_certs=False,
        timeout=60,
        max_retries=10,
        retry_on_timeout=True
    )

# OpenSearch 클라이언트 생성
client = create_opensearch_client()

# ============================================================================
# 인덱스 설정 및 매핑 정의 (로컬 OpenSearch용)
# ============================================================================

RECIPE_INDEX = 'recipes'
INGREDIENT_INDEX = 'ingredients'

# 레시피 인덱스 매핑 설정 (로컬 OpenSearch용)
recipe_mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # 로컬에서는 복제본 불필요
        "analysis": {
            "analyzer": {
                "korean_analyzer": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["lowercase", "nori_part_of_speech"]
                }
            },
            "tokenizer": {
                "nori_tokenizer": {
                    "type": "nori_tokenizer",
                    "decompound_mode": "mixed"
                }
            },
            "filter": {
                "nori_part_of_speech": {
                    "type": "nori_part_of_speech",
                    "stoptags": ["E", "IC", "J", "MAG", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "recipe_id": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "korean_analyzer"},
            "ingredients": {"type": "text", "analyzer": "korean_analyzer"},
            "category": {"type": "keyword"},
            "cooking_method": {"type": "keyword"},
            "hashtag": {"type": "text", "analyzer": "korean_analyzer"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    }
}

# 재료 인덱스 매핑 설정 (로컬 OpenSearch용)
ingredient_mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # 로컬에서는 복제본 불필요
        "analysis": {
            "analyzer": {
                "korean_analyzer": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["lowercase", "nori_part_of_speech"]
                }
            },
            "tokenizer": {
                "nori_tokenizer": {
                    "type": "nori_tokenizer",
                    "decompound_mode": "mixed"
                }
            },
            "filter": {
                "nori_part_of_speech": {
                    "type": "nori_part_of_speech",
                    "stoptags": ["E", "IC", "J", "MAG", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "ingredient_id": {"type": "long"},
            "name": {"type": "text", "analyzer": "korean_analyzer"},
            "aliases": {"type": "text", "analyzer": "korean_analyzer"},
            "category": {"type": "keyword"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    }
}

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def test_connection():
    """로컬 OpenSearch 서버와의 연결을 테스트합니다."""
    try:
        info = client.info()
        print(f" 로컬 OpenSearch 연결 성공!")
        print(f"   - 버전: {info['version']['number']}")
        print(f"   - 클러스터: {info['cluster_name']}")
        return True
    except Exception as e:
        print(f" 로컬 OpenSearch 연결 실패: {e}")
        return False

def delete_index_if_exists(index_name):
    """인덱스가 존재하면 삭제합니다."""
    try:
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"🗑️ 기존 인덱스 삭제: {index_name}")
            time.sleep(2)
    except Exception as e:
        print(f" 인덱스 삭제 중 오류 (무시됨): {e}")

def create_index(index_name, mapping):
    """로컬 OpenSearch에 인덱스를 생성합니다."""
    try:
        delete_index_if_exists(index_name)
        response = client.indices.create(index=index_name, body=mapping)
        print(f" 인덱스 생성 완료: {index_name}")
        time.sleep(3)
        return True
    except Exception as e:
        print(f" 인덱스 생성 실패 {index_name}: {e}")
        return False

def validate_embedding_data(data):
    """임베딩 데이터의 유효성을 검사합니다."""
    valid_data = []
    
    for item in data:
        embedding = item.get('embedding')
        
        if embedding and isinstance(embedding, list) and len(embedding) == 1536:
            if all(isinstance(x, (int, float)) for x in embedding):
                valid_data.append(item)
            else:
                print(f"⚠️ 임베딩 값이 숫자가 아님: {item.get('name', item.get('recipe_id', 'Unknown'))}")
        else:
            print(f"⚠️ 잘못된 임베딩 차원: {item.get('name', item.get('recipe_id', 'Unknown'))}")
    
    print(f" 유효한 데이터: {len(valid_data)}/{len(data)}")
    return valid_data

def bulk_upload(index_name, data, batch_size=50):
    """로컬 OpenSearch에 대량 데이터를 배치 업로드합니다."""
    actions = []
    total = len(data)
    success_count = 0
    error_count = 0
    
    print(f" {index_name} 업로드 시작: {total}개 문서")
    
    for i, item in enumerate(data, 1):
        # 문서 ID 설정
        doc_id = None
        if 'recipe_id' in item:
            doc_id = item['recipe_id']
        elif 'ingredient_id' in item:
            doc_id = item['ingredient_id']
        
        action = {
            "_index": index_name,
            "_source": item
        }
        
        if doc_id:
            action["_id"] = str(doc_id)
            
        actions.append(action)
        
        # 배치 크기에 도달하거나 마지막 문서인 경우
        if len(actions) >= batch_size or i == total:
            try:
                # 대량 업로드 실행
                success, errors = helpers.bulk(
                    client, 
                    actions, 
                    timeout=300,
                    max_retries=3,
                    initial_backoff=1,
                    max_backoff=60
                )
                
                # 성공/실패 카운팅
                success_count += success
                
                # 오류 처리
                if errors:
                    error_count += len(errors)
                    print(f"   ⚠️ 배치 오류 {len(errors)}개")
                
                # 진행률 출력
                print(f"   진행상황: {i}/{total} ({(i/total)*100:.1f}%) - 성공: {success_count}, 실패: {error_count}")
                
                actions = []
                time.sleep(0.5)  # API 부하 방지
                
            except Exception as e:
                print(f" 배치 업로드 오류: {e}")
                error_count += len(actions)
                actions = []
    
    print(f" {index_name} 업로드 완료: 성공 {success_count}/{total}, 실패 {error_count}")
    return success_count > (total * 0.8)  # 80% 이상 성공하면 OK

def verify_upload():
    """업로드된 데이터를 검증합니다."""
    print("\\n📋 업로드 결과 검증:")
    
    time.sleep(3)  # 인덱싱 완료 대기
    
    # 레시피 인덱스 확인
    try:
        recipe_count = client.count(index=RECIPE_INDEX)["count"]
        print(f"    레시피: {recipe_count}개")
        
        sample = client.search(index=RECIPE_INDEX, body={"query": {"match_all": {}}, "size": 1})
        if sample["hits"]["hits"]:
            sample_recipe = sample["hits"]["hits"][0]["_source"]
            print(f"    샘플 레시피: {sample_recipe.get('name', 'N/A')}")
            print(f"    임베딩 차원: {len(sample_recipe.get('embedding', []))}")
            
    except Exception as e:
        print(f"    레시피 확인 실패: {e}")
    
    # 재료 인덱스 확인
    try:
        ingredient_count = client.count(index=INGREDIENT_INDEX)["count"]
        print(f"    재료: {ingredient_count}개")
        
        sample = client.search(index=INGREDIENT_INDEX, body={"query": {"match_all": {}}, "size": 1})
        if sample["hits"]["hits"]:
            sample_ingredient = sample["hits"]["hits"][0]["_source"]
            print(f"    샘플 재료: {sample_ingredient.get('name', 'N/A')}")
            print(f"    카테고리: {sample_ingredient.get('category', 'N/A')}")
            
    except Exception as e:
        print(f"    재료 확인 실패: {e}")

def test_vector_search():
    """벡터 검색 기능을 테스트합니다."""
    print("\\n 벡터 검색 테스트:")
    
    try:
        # 더미 벡터로 기본 기능 확인
        dummy_vector = [0.1] * 1536
        
        dummy_search = client.search(
            index=INGREDIENT_INDEX,
            body={
                "size": 3,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                            "params": {"query_vector": dummy_vector}
                        }
                    }
                }
            }
        )

        
        if (dummy_search and 
            dummy_search.get("hits") and 
            dummy_search["hits"].get("hits")):
            print(f"    벡터 검색 성공: {len(dummy_search['hits']['hits'])}개 결과")
            for i, hit in enumerate(dummy_search['hits']['hits'], 1):
                source = hit.get("_source", {})
                score = hit.get("_score", 0)
                name = source.get('name', 'Unknown')
                print(f"      {i}. {name} - 점수: {score:.3f}")
        else:
            print("    벡터 검색 실패")
        
    except Exception as e:
        print(f"    벡터 검색 테스트 실패: {e}")

# ============================================================================
# 메인 실행 함수
# ============================================================================

def main():
    """메인 실행 함수"""
    print(" 로컬 OpenSearch 벡터 데이터 업로드 시작\\n")
    
    # 1. 환경변수 확인
    required_vars = ['OPENSEARCH_HOST']
    for var in required_vars:
        if not os.getenv(var):
            print(f" {var} 환경변수가 설정되지 않았습니다")
            return
    
    # 2. OpenSearch 연결 테스트
    if not test_connection():
        return
    
    # 3. 인덱스 생성
    print("\\n 인덱스 생성:")
    if not create_index(RECIPE_INDEX, recipe_mapping):
        return
    if not create_index(INGREDIENT_INDEX, ingredient_mapping):
        return
    
    # 4. 데이터 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print("\\n 데이터 업로드:")
    
    # 5-1. 레시피 데이터 업로드
    recipe_files = [
        os.path.join(project_root, "data", "recipe_embeddings.json"),
        os.path.join(current_dir, "recipe_embeddings.json"),
        "../data/recipe_embeddings.json"
    ]
    
    recipe_uploaded = False
    for recipe_file in recipe_files:
        if os.path.exists(recipe_file):
            print(f" 레시피 파일 로드: {recipe_file}")
            try:
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)
                
                valid_recipes = validate_embedding_data(recipes)
                if valid_recipes:
                    bulk_upload(RECIPE_INDEX, valid_recipes)
                    recipe_uploaded = True
                    break
                else:
                    print(" 유효한 레시피 데이터가 없습니다")
                    
            except Exception as e:
                print(f" 레시피 파일 로드 실패: {e}")
    
    if not recipe_uploaded:
        print(" 레시피 파일을 찾을 수 없습니다")
    
    # 5-2. 재료 데이터 업로드
    ingredient_files = [
        os.path.join(project_root, "data", "ingredient_embeddings.json"),
        os.path.join(current_dir, "ingredient_embeddings.json"),
        "../data/ingredient_embeddings.json"
    ]
    
    ingredient_uploaded = False
    for ingredient_file in ingredient_files:
        if os.path.exists(ingredient_file):
            print(f" 재료 파일 로드: {ingredient_file}")
            try:
                with open(ingredient_file, 'r', encoding='utf-8') as f:
                    ingredients = json.load(f)
                
                valid_ingredients = validate_embedding_data(ingredients)
                if valid_ingredients:
                    # 재료 데이터 전처리
                    processed_ingredients = []
                    for ingredient in valid_ingredients:
                        aliases = ingredient.get('aliases', [])
                        if isinstance(aliases, list):
                            aliases_text = ' '.join(str(alias) for alias in aliases)
                        else:
                            aliases_text = str(aliases)
                        
                        processed_item = {
                            "ingredient_id": ingredient.get('ingredient_id'),
                            "name": ingredient.get('name'),
                            "aliases": aliases_text,
                            "category": ingredient.get('category'),
                            "embedding": ingredient.get('embedding'),
                            "embedding_text": ingredient.get('embedding_text'),
                            "created_at": ingredient.get('created_at')
                        }
                        processed_ingredients.append(processed_item)
                    
                    bulk_upload(INGREDIENT_INDEX, processed_ingredients)
                    ingredient_uploaded = True
                    break
                else:
                    print(" 유효한 재료 데이터가 없습니다")
                    
            except Exception as e:
                print(f" 재료 파일 로드 실패: {e}")
    
    if not ingredient_uploaded:
        print(" 재료 파일을 찾을 수 없습니다")
    
    # 6. 업로드 결과 검증
    verify_upload()
    
    # 7. 벡터 검색 테스트
    test_vector_search()
    
    print("\\n 로컬 OpenSearch 업로드 완료!")
    print("\\n 다음 단계:")
    print("   1. AI 서버에서 벡터 검색 API 구현")
    print("   2. Java 백엔드와 연동")
    print("   3. 레시피 추천 시스템 통합 테스트")

def check_only():
    """업로드 없이 현재 상태만 확인하는 함수"""
    print("🔍 OpenSearch 상태 확인만 실행\\n")
    
    if not test_connection():
        return
    
    verify_upload()
    test_vector_search()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_only()
    else:
        main()
