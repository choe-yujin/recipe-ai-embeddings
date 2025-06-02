# ============================================================================
# Local OpenSearch 데이터 업로드 스크립트 (로컬 환경용)
# ============================================================================
# 목적: 1136개 레시피와 약 500개 재료의 벡터 임베딩을 로컬 OpenSearch에 업로드
# 사용법: python upload_to_opensearch.py
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
# OpenSearch 클라이언트 설정
# ============================================================================

def create_opensearch_client():
    """로컬 OpenSearch 클라이언트를 생성합니다."""
    host = os.getenv('OPENSEARCH_HOST', 'localhost')
    port = int(os.getenv('OPENSEARCH_PORT', '9201'))
    
    print("🔑 로컬 OpenSearch 접근")
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
if not client:
    print("❌ OpenSearch 클라이언트 생성 실패")
    exit(1)

# ============================================================================
# 인덱스 설정 및 매핑 정의 (AWS OpenSearch 호환)
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
        print(f"✅ 로컬 OpenSearch 연결 성공!")
        print(f"   - 버전: {info['version']['number']}")
        print(f"   - 클러스터: {info['cluster_name']}")
        return True
    except Exception as e:
        print(f"❌ 로컬 OpenSearch 연결 실패: {e}")
        return False

def delete_index_if_exists(index_name):
    """인덱스가 존재하면 삭제합니다."""
    try:
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"🗑️ 기존 인덱스 삭제: {index_name}")
            time.sleep(2)
    except Exception as e:
        print(f"⚠️ 인덱스 삭제 중 오류 (무시됨): {e}")

def create_index(index_name, mapping):
    """로컬 OpenSearch에 인덱스를 생성합니다."""
    try:
        delete_index_if_exists(index_name)
        response = client.indices.create(index=index_name, body=mapping)
        print(f"✅ 인덱스 생성 완료: {index_name}")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"❌ 인덱스 생성 실패 {index_name}: {e}")
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
    
    print(f"📊 유효한 데이터: {len(valid_data)}/{len(data)}")
    return valid_data

def preprocess_ingredient_data(ingredients):
    """재료 데이터를 AWS OpenSearch 업로드용으로 전처리합니다."""
    processed = []
    
    for ingredient in ingredients:
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
        processed.append(processed_item)
    
    return processed

def preprocess_recipe_data(recipes):
    """레시피 데이터를 전처리합니다."""
    return recipes

def bulk_upload(index_name, data, batch_size=20):
    """
    대량의 데이터를 AWS OpenSearch에 배치 업로드합니다.
    정확한 성공/실패 카운팅과 오류 로그를 제공합니다.
    """
    actions = []
    total = len(data)
    success_count = 0
    error_count = 0
    
    print(f"📤 {index_name} 업로드 시작: {total}개 문서")
    
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
                    timeout=600,
                    max_retries=3,
                    initial_backoff=2,
                    max_backoff=300
                )
                
                # 성공/실패 카운팅
                success_count += success
                
                # 오류 처리
                if errors:
                    error_count += len(errors)
                    print(f"   ⚠️ 배치 오류 {len(errors)}개:")
                    for error in errors[:3]:  # 처음 3개 오류만 표시
                        error_info = error.get('index', {}).get('error', {})
                        error_type = error_info.get('type', 'unknown')
                        error_reason = error_info.get('reason', 'unknown reason')
                        print(f"      - {error_type}: {error_reason}")
                    if len(errors) > 3:
                        print(f"      - ... 및 {len(errors)-3}개 추가 오류")
                
                # 진행률 출력
                print(f"   진행상황: {i}/{total} ({(i/total)*100:.1f}%) - 성공: {success_count}, 실패: {error_count}")
                
                actions = []
                time.sleep(1)  # API 부하 방지
                
            except Exception as e:
                print(f"❌ 배치 업로드 심각한 오류: {e}")
                error_count += len(actions)
                
                # 개별 업로드 시도
                individual_success = 0
                for j, action in enumerate(actions):
                    try:
                        response = client.index(
                            index=action["_index"], 
                            body=action["_source"], 
                            id=action.get("_id"),
                            timeout=60
                        )
                        if response.get('result') in ['created', 'updated']:
                            individual_success += 1
                    except Exception as individual_error:
                        print(f"   개별 업로드 실패 [{j+1}]: {str(individual_error)[:100]}...")
                
                success_count += individual_success
                error_count = error_count - len(actions) + (len(actions) - individual_success)
                actions = []
    
    print(f"✅ {index_name} 업로드 완료: 성공 {success_count}/{total}, 실패 {error_count}")
    return success_count == total

def verify_upload():
    """업로드된 데이터를 검증합니다."""
    print("\n📋 업로드 결과 검증:")
    
    time.sleep(5)  # 인덱싱 완료 대기
    
    # 레시피 인덱스 확인
    try:
        recipe_count = client.count(index=RECIPE_INDEX)["count"]
        print(f"   📊 레시피: {recipe_count}개")
        
        sample = client.search(index=RECIPE_INDEX, body={"query": {"match_all": {}}, "size": 1})
        if sample["hits"]["hits"]:
            sample_recipe = sample["hits"]["hits"][0]["_source"]
            print(f"   📝 샘플 레시피: {sample_recipe.get('name', 'N/A')}")
            print(f"   🔢 임베딩 차원: {len(sample_recipe.get('embedding', []))}")
            
    except Exception as e:
        print(f"   ❌ 레시피 확인 실패: {e}")
    
    # 재료 인덱스 확인
    try:
        ingredient_count = client.count(index=INGREDIENT_INDEX)["count"]
        print(f"   📊 재료: {ingredient_count}개")
        
        sample = client.search(index=INGREDIENT_INDEX, body={"query": {"match_all": {}}, "size": 1})
        if sample["hits"]["hits"]:
            sample_ingredient = sample["hits"]["hits"][0]["_source"]
            print(f"   📝 샘플 재료: {sample_ingredient.get('name', 'N/A')}")
            print(f"   🏷️ 카테고리: {sample_ingredient.get('category', 'N/A')}")
            
    except Exception as e:
        print(f"   ❌ 재료 확인 실패: {e}")

def test_simple_upload():
    """간단한 테스트 문서로 업로드 기능을 테스트합니다."""
    print("\n🧪 간단한 업로드 테스트:")
    
    try:
        test_doc = {
            "recipe_id": "test_001",
            "name": "테스트 레시피",
            "ingredients": "테스트 재료",
            "category": "테스트",
            "cooking_method": "테스트",
            "hashtag": "테스트",
            "embedding": [0.1] * 1536,
            "embedding_text": "테스트용 임베딩 텍스트",
            "created_at": "2025-05-30T00:00:00Z"
        }
        
        response = client.index(
            index="recipes",
            body=test_doc,
            id="test_001",
            timeout=60
        )
        
        print(f"   ✅ 테스트 문서 업로드 성공: {response['result']}")
        
        # 테스트 문서 삭제
        client.delete(index="recipes", id="test_001")
        return True
        
    except Exception as e:
        print(f"   ❌ 테스트 업로드 실패: {e}")
        return False

def test_vector_search():
    """벡터 검색 기능을 자연어로 테스트합니다."""
    print("\n🧪 벡터 검색 테스트:")
    
    try:
        # 1. 기존 데이터에서 샘플 임베딩 가져오기
        print("\n   🔍 재료 벡터 검색 테스트:")
        
        # 샘플 재료 검색 (밀가루와 유사한 재료 찾기)
        sample_ingredient = client.search(
            index=INGREDIENT_INDEX,
            body={"query": {"match": {"name": "밀가루"}}, "size": 1}
        )
        
        if (sample_ingredient and 
            sample_ingredient.get("hits") and 
            sample_ingredient["hits"].get("hits") and 
            len(sample_ingredient["hits"]["hits"]) > 0):
            
            flour_data = sample_ingredient["hits"]["hits"][0]["_source"]
            flour_embedding = flour_data.get("embedding")
            
            if flour_embedding and len(flour_embedding) == 1536:
                print(f"   📝 검색 기준: '밀가루' (곡류/분말)")
                
                # 밀가루와 유사한 재료 검색 (로컬 OpenSearch용)
                similar_ingredients = client.search(
                    index=INGREDIENT_INDEX,
                    body={
                        "size": 5,
                        "query": {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {"query_vector": flour_embedding}
                                }
                            }
                        }
                    }
                )
                
                if (similar_ingredients and 
                    similar_ingredients.get("hits") and 
                    similar_ingredients["hits"].get("hits")):
                    
                    print(f"   ✅ 유사한 재료 {len(similar_ingredients['hits']['hits'])}개 발견:")
                    for i, hit in enumerate(similar_ingredients['hits']['hits'][:3], 1):
                        source = hit.get("_source", {})
                        score = hit.get("_score", 0)
                        name = source.get('name', 'Unknown')
                        category = source.get('category', 'Unknown')
                        print(f"      {i}. {name} ({category}) - 유사도: {score:.3f}")
                else:
                    print("   ❌ 유사한 재료를 찾을 수 없습니다")
            else:
                print("   ❌ 밀가루의 임베딩 데이터가 올바르지 않습니다")
        else:
            print("   ❌ '밀가루' 재료를 찾을 수 없습니다")
        
        print("\n   🔍 레시피 벡터 검색 테스트:")
        
        # 샘플 레시피 검색 (볶음 요리와 유사한 레시피 찾기)
        sample_recipe = client.search(
            index=RECIPE_INDEX,
            body={"query": {"match": {"name": "볶음"}}, "size": 1}
        )
        
        if (sample_recipe and 
            sample_recipe.get("hits") and 
            sample_recipe["hits"].get("hits") and 
            len(sample_recipe["hits"]["hits"]) > 0):
            
            recipe_data = sample_recipe["hits"]["hits"][0]["_source"]
            stir_fry_embedding = recipe_data.get("embedding")
            recipe_name = recipe_data.get("name", "Unknown Recipe")
            
            if stir_fry_embedding and len(stir_fry_embedding) == 1536:
                print(f"   📝 검색 기준: '{recipe_name}' (볶음 요리)")
                
                # 볶음과 유사한 레시피 검색 (로컬 OpenSearch용)
                similar_recipes = client.search(
                    index=RECIPE_INDEX,
                    body={
                        "size": 5,
                        "query": {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {"query_vector": stir_fry_embedding}
                                }
                            }
                        }
                    }
                )
                
                if (similar_recipes and 
                    similar_recipes.get("hits") and 
                    similar_recipes["hits"].get("hits")):
                    
                    print(f"   ✅ 유사한 레시피 {len(similar_recipes['hits']['hits'])}개 발견:")
                    for i, hit in enumerate(similar_recipes['hits']['hits'][:3], 1):
                        source = hit.get("_source", {})
                        score = hit.get("_score", 0)
                        name = source.get('name', 'Unknown Recipe')
                        ingredients = source.get('ingredients', '')
                        category = source.get('category', 'N/A')
                        
                        ingredients_preview = ingredients[:30] + "..." if len(ingredients) > 30 else ingredients
                        print(f"      {i}. {name} - 유사도: {score:.3f}")
                        print(f"         재료: {ingredients_preview}")
                        print(f"         카테고리: {category}")
                else:
                    print("   ❌ 유사한 레시피를 찾을 수 없습니다")
            else:
                print("   ❌ 레시피의 임베딩 데이터가 올바르지 않습니다")
        else:
            print("   ❌ '볶음' 레시피를 찾을 수 없습니다")
        
        # 3. 특정 재료 기반 레시피 추천 테스트
        print("\n   🔍 특정 재료 기반 레시피 추천 테스트:")
        
        # 닭고기 임베딩 가져오기
        chicken_search = client.search(
            index=INGREDIENT_INDEX,
            body={"query": {"match": {"name": "닭고기"}}, "size": 1}
        )
        
        if (chicken_search and 
            chicken_search.get("hits") and 
            chicken_search["hits"].get("hits") and 
            len(chicken_search["hits"]["hits"]) > 0):
            
            chicken_data = chicken_search["hits"]["hits"][0]["_source"]
            chicken_embedding = chicken_data.get("embedding")
            
            if chicken_embedding and len(chicken_embedding) == 1536:
                print(f"   📝 검색 재료: '닭고기'")
                
                # 닭고기를 사용하는 레시피 검색 (로컬 OpenSearch용)
                chicken_recipes = client.search(
                    index=RECIPE_INDEX,
                    body={
                        "size": 3,
                        "query": {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {"query_vector": chicken_embedding}
                                }
                            }
                        }
                    }
                )
                
                if (chicken_recipes and 
                    chicken_recipes.get("hits") and 
                    chicken_recipes["hits"].get("hits")):
                    
                    print(f"   ✅ 닭고기 활용 레시피 추천:")
                    for i, hit in enumerate(chicken_recipes['hits']['hits'], 1):
                        source = hit.get("_source", {})
                        score = hit.get("_score", 0)
                        name = source.get('name', 'Unknown Recipe')
                        ingredients = source.get('ingredients', '')
                        
                        print(f"      {i}. {name} - 관련도: {score:.3f}")
                        if '닭' in ingredients:
                            print(f"         ✓ 닭고기 포함 확인")
                        else:
                            print(f"         - 닭고기 직접 포함되지 않음")
                else:
                    print("   ❌ 닭고기 활용 레시피를 찾을 수 없습니다")
            else:
                print("   ❌ 닭고기의 임베딩 데이터가 올바르지 않습니다")
        else:
            print("   ❌ '닭고기' 재료를 찾을 수 없습니다")
        
        # 4. 간단한 더미 벡터 검색 (기본 기능 확인)
        print("\n   🔍 기본 벡터 검색 기능 테스트:")
        
        dummy_vector = [0.1] * 1536
        
        dummy_search = client.search(
            index=INGREDIENT_INDEX,
            body={
                "size": 3,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": dummy_vector}
                        }
                    }
                }
            }
        )
        
        if (dummy_search and 
            dummy_search.get("hits") and 
            dummy_search["hits"].get("hits")):
            print(f"   ✅ 더미 벡터 검색 성공: {len(dummy_search['hits']['hits'])}개 결과")
        else:
            print("   ❌ 더미 벡터 검색 실패")
        
    except Exception as e:
        print(f"   ❌ 벡터 검색 테스트 실패: {e}")
        print(f"   오류 세부사항: {str(e)}")
        
        # 추가 디버깅 정보
        try:
            # 인덱스 존재 확인
            recipe_exists = client.indices.exists(index=RECIPE_INDEX)
            ingredient_exists = client.indices.exists(index=INGREDIENT_INDEX)
            print(f"   🔍 디버깅: recipes 인덱스 존재: {recipe_exists}")
            print(f"   🔍 디버깅: ingredients 인덱스 존재: {ingredient_exists}")
            
            # 문서 수 확인
            if recipe_exists:
                recipe_count = client.count(index=RECIPE_INDEX).get("count", 0)
                print(f"   🔍 디버깅: recipes 문서 수: {recipe_count}")
            
            if ingredient_exists:
                ingredient_count = client.count(index=INGREDIENT_INDEX).get("count", 0)
                print(f"   🔍 디버깅: ingredients 문서 수: {ingredient_count}")
                
        except Exception as debug_error:
            print(f"   🔍 디버깅 정보 수집 실패: {debug_error}")

def test_natural_language_search():
    """자연어 검색 시뮬레이션 (텍스트 + 벡터 조합)"""
    print("\n🗣️ 자연어 검색 시뮬레이션:")
    
    search_scenarios = [
        {
            "query": "간단한 아침 요리",
            "description": "아침에 만들기 쉬운 요리 찾기",
            "keywords": ["간단", "아침", "쉬운"]
        },
        {
            "query": "매운 닭고기 요리",
            "description": "매운맛 닭고기 레시피 찾기", 
            "keywords": ["매운", "닭", "고추"]
        },
        {
            "query": "건강한 채소 요리",
            "description": "영양가 있는 채소 중심 요리",
            "keywords": ["건강", "채소", "영양"]
        }
    ]
    
    for scenario in search_scenarios:
        print(f"\n   🔍 시나리오: '{scenario['query']}'")
        print(f"   📝 설명: {scenario['description']}")
        
        try:
            # 키워드 기반 텍스트 검색
            text_results = client.search(
                index=RECIPE_INDEX,
                body={
                    "size": 3,
                    "query": {
                        "multi_match": {
                            "query": " ".join(scenario['keywords']),
                            "fields": ["name^2", "ingredients", "hashtag"],
                            "type": "best_fields"
                        }
                    }
                }
            )
            
            print(f"   ✅ 텍스트 검색 결과 ({len(text_results['hits']['hits'])}개):")
            for i, hit in enumerate(text_results['hits']['hits'], 1):
                source = hit["_source"]
                score = hit["_score"]
                print(f"      {i}. {source['name']} - 점수: {score:.3f}")
                print(f"         해시태그: {source.get('hashtag', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ 시나리오 '{scenario['query']}' 검색 실패: {e}")

def test_ingredient_combination_search():
    """재료 조합 기반 레시피 검색 테스트"""
    print("\n🥘 재료 조합 레시피 검색 테스트:")
    
    ingredient_combinations = [
        ["계란", "밀가루"],
        ["닭고기", "양파", "간장"],
        ["돼지고기", "배추", "고춧가루"]
    ]
    
    for ingredients in ingredient_combinations:
        print(f"\n   🔍 재료 조합: {' + '.join(ingredients)}")
        
        try:
            # 다중 재료 검색
            should_queries = []
            for ingredient in ingredients:
                should_queries.append({"match": {"ingredients": ingredient}})
            
            combo_results = client.search(
                index=RECIPE_INDEX,
                body={
                    "size": 3,
                    "query": {
                        "bool": {
                            "should": should_queries,
                            "minimum_should_match": len(ingredients) - 1  # 최소 n-1개 재료 포함
                        }
                    }
                }
            )
            
            print(f"   ✅ 추천 레시피 ({len(combo_results['hits']['hits'])}개):")
            for i, hit in enumerate(combo_results['hits']['hits'], 1):
                source = hit["_source"]
                score = hit["_score"]
                
                # 포함된 재료 확인
                included_ingredients = []
                for ing in ingredients:
                    if ing in source.get('ingredients', ''):
                        included_ingredients.append(ing)
                
                print(f"      {i}. {source['name']} - 점수: {score:.3f}")
                print(f"         포함 재료: {', '.join(included_ingredients) if included_ingredients else '없음'}")
                print(f"         조리법: {source.get('cooking_method', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ 재료 조합 검색 실패: {e}")

def detailed_status_check():
    """상세한 OpenSearch 상태를 확인합니다."""
    print("\n🔍 상세 상태 확인:")
    
    try:
        # 클러스터 상태
        cluster_health = client.cluster.health()
        print(f"   🏥 클러스터 상태: {cluster_health['status']}")
        print(f"   📊 활성 샤드: {cluster_health['active_shards']}")
        print(f"   🔄 재배치 중인 샤드: {cluster_health['relocating_shards']}")
        
        # 인덱스 상태
        indices_stats = client.indices.stats(index=[RECIPE_INDEX, INGREDIENT_INDEX])
        
        if RECIPE_INDEX in indices_stats['indices']:
            recipe_stats = indices_stats['indices'][RECIPE_INDEX]
            print(f"   📈 레시피 인덱스 크기: {recipe_stats['total']['store']['size_in_bytes']} bytes")
            print(f"   📝 레시피 문서 수: {recipe_stats['total']['docs']['count']}")
        
        if INGREDIENT_INDEX in indices_stats['indices']:
            ingredient_stats = indices_stats['indices'][INGREDIENT_INDEX]
            print(f"   📈 재료 인덱스 크기: {ingredient_stats['total']['store']['size_in_bytes']} bytes")
            print(f"   📝 재료 문서 수: {ingredient_stats['total']['docs']['count']}")
            
        # 샘플 검색
        print("\n   🔍 샘플 검색 테스트:")
        
        # 텍스트 검색
        text_search = client.search(
            index=RECIPE_INDEX,
            body={"query": {"match": {"name": "볶음"}}, "size": 1}
        )
        print(f"   📝 '볶음' 텍스트 검색: {text_search['hits']['total']['value']}개 결과")
        
        # 카테고리 검색
        category_search = client.search(
            index=INGREDIENT_INDEX,
            body={"query": {"term": {"category": "곡류/분말"}}, "size": 1}
        )
        print(f"   🏷️ '곡류/분말' 카테고리 검색: {category_search['hits']['total']['value']}개 결과")
        
    except Exception as e:
        print(f"   ❌ 상태 확인 실패: {e}")

# ============================================================================
# 메인 실행 함수
# ============================================================================

def main():
    """메인 실행 함수"""
    print("🚀 AWS OpenSearch 벡터 데이터 업로드 시작\n")
    
    # 1. 환경변수 확인
    required_vars = ['OPENSEARCH_HOST']
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ {var} 환경변수가 설정되지 않았습니다")
            return
    
    if not (os.getenv('OPENSEARCH_USERNAME') and os.getenv('OPENSEARCH_PASSWORD')):
        if not os.getenv('AWS_REGION'):
            print("❌ 인증 정보가 부족합니다.")
            return
    
    # 2. OpenSearch 연결 테스트
    if not test_connection():
        return
    
    # 3. 인덱스 생성
    print("\n📂 인덱스 생성:")
    if not create_index(RECIPE_INDEX, recipe_mapping):
        return
    if not create_index(INGREDIENT_INDEX, ingredient_mapping):
        return
    
    # 3.5. 간단한 업로드 테스트
    if not test_simple_upload():
        print("❌ 기본 업로드 테스트 실패. 설정을 확인해주세요.")
        return
    
    # 4. 데이터 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print("\n📤 데이터 업로드:")
    
    # 5-1. 레시피 데이터 업로드
    recipe_files = [
        os.path.join(project_root, "data", "recipe_embeddings.json"),
        os.path.join(current_dir, "recipe_embeddings.json"),
        "../data/recipe_embeddings.json"
    ]
    
    recipe_uploaded = False
    for recipe_file in recipe_files:
        if os.path.exists(recipe_file):
            print(f"📁 레시피 파일 로드: {recipe_file}")
            try:
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)
                
                valid_recipes = validate_embedding_data(recipes)
                if valid_recipes:
                    processed_recipes = preprocess_recipe_data(valid_recipes)
                    bulk_upload(RECIPE_INDEX, processed_recipes)
                    recipe_uploaded = True
                    break
                else:
                    print("❌ 유효한 레시피 데이터가 없습니다")
                    
            except Exception as e:
                print(f"❌ 레시피 파일 로드 실패: {e}")
    
    if not recipe_uploaded:
        print("❌ 레시피 파일을 찾을 수 없습니다")
    
    # 5-2. 재료 데이터 업로드
    ingredient_files = [
        os.path.join(project_root, "data", "ingredient_embeddings.json"),
        os.path.join(current_dir, "ingredient_embeddings.json"),
        "../data/ingredient_embeddings.json"
    ]
    
    ingredient_uploaded = False
    for ingredient_file in ingredient_files:
        if os.path.exists(ingredient_file):
            print(f"📁 재료 파일 로드: {ingredient_file}")
            try:
                with open(ingredient_file, 'r', encoding='utf-8') as f:
                    ingredients = json.load(f)
                
                valid_ingredients = validate_embedding_data(ingredients)
                if valid_ingredients:
                    processed_ingredients = preprocess_ingredient_data(valid_ingredients)
                    bulk_upload(INGREDIENT_INDEX, processed_ingredients)
                    ingredient_uploaded = True
                    break
                else:
                    print("❌ 유효한 재료 데이터가 없습니다")
                    
            except Exception as e:
                print(f"❌ 재료 파일 로드 실패: {e}")
    
    if not ingredient_uploaded:
        print("❌ 재료 파일을 찾을 수 없습니다")
    
    # 6. 업로드 결과 검증
    verify_upload()
    
    # 7. 벡터 검색 테스트
    test_vector_search()
    
    # 8. 자연어 검색 테스트
    test_natural_language_search()
    
    # 9. 재료 조합 검색 테스트
    test_ingredient_combination_search()
    
    # 8. 상세 상태 확인
    detailed_status_check()
    
    print("\n🎉 로컬 OpenSearch 업로드 완료!")
    print("\n📖 다음 단계:")
    print("   1. AI 서버에서 벡터 검색 API 구현")
    print("   2. Java 백엔드와 연동")
    print("   3. 레시피 추천 시스템 통합 테스트")

def check_only():
    """업로드 없이 현재 상태만 확인하는 함수"""
    print("🔍 OpenSearch 상태 확인만 실행\n")
    
    if not test_connection():
        return
    
    verify_upload()
    test_vector_search()
    test_natural_language_search()
    test_ingredient_combination_search()
    detailed_status_check()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_only()
    else:
        main()