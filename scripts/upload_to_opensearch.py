# ============================================================================
# AWS OpenSearch 데이터 업로드 스크립트 (AWS OpenSearch 호환 버전)
# ============================================================================
# 목적: 1136개 레시피와 약 500개 재료의 벡터 임베딩을 AWS OpenSearch에 업로드
# 사용법: python upload_to_opensearch.py
# 필수 환경변수: OPENSEARCH_HOST, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD
# ============================================================================

import json
import os
from opensearchpy import OpenSearch, helpers
from dotenv import load_dotenv
import time

# .env 파일에서 환경변수 로드
# OPENSEARCH_HOST, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD 등을 설정
load_dotenv()

# ============================================================================
# OpenSearch 클라이언트 설정
# ============================================================================

def create_opensearch_client():
    """
    AWS OpenSearch 클라이언트를 생성합니다.
    
    두 가지 인증 방식을 지원:
    1. Username/Password 인증 (Fine-grained access control)
    2. AWS IAM 인증 (VPC 내부에서 사용)
    
    Returns:
        OpenSearch: 설정된 OpenSearch 클라이언트 객체
    """
    host = os.getenv('OPENSEARCH_HOST')
    username = os.getenv('OPENSEARCH_USERNAME')
    password = os.getenv('OPENSEARCH_PASSWORD')
    
    if username and password:
        # Username/Password 인증 방식 (추천)
        print("🔑 Username/Password 인증 사용")
        return OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=(username, password),
            use_ssl=True,                    # HTTPS 사용
            verify_certs=True,               # SSL 인증서 검증
            ssl_show_warn=False,             # SSL 경고 숨김
            timeout=60,                      # 연결 타임아웃 60초 (벡터 업로드용)
            max_retries=10,                  # 최대 재시도 횟수
            retry_on_timeout=True            # 타임아웃 시 재시도
        )
    else:
        # AWS IAM 인증 방식 (VPC 내부에서 사용)
        print("🔑 IAM 인증 사용")
        try:
            import boto3
            from requests_aws4auth import AWS4Auth
            
            region = os.getenv('AWS_REGION', 'ap-northeast-2')
            service = 'es'
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
            
            return OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                ssl_show_warn=False,
                timeout=60,
                max_retries=10,
                retry_on_timeout=True
            )
        except ImportError:
            print("❌ boto3 또는 requests_aws4auth 패키지가 필요합니다")
            print("pip install boto3 requests_aws4auth")
            return None

# OpenSearch 클라이언트 생성
client = create_opensearch_client()
if not client:
    print("❌ OpenSearch 클라이언트 생성 실패")
    exit(1)

# ============================================================================
# 인덱스 설정 및 매핑 정의 (AWS OpenSearch 호환)
# ============================================================================

# 인덱스 이름 상수 정의
RECIPE_INDEX = 'recipes'        # 레시피 인덱스명
INGREDIENT_INDEX = 'ingredients' # 재료 인덱스명

# 레시피 인덱스 매핑 설정 (AWS OpenSearch kNN 방식)
recipe_mapping = {
    "settings": {
        "index": {
            "knn": True,                    # kNN 기능 활성화
            "knn.algo_param.ef_search": 100,  # kNN 검색 파라미터
            "knn.space_type": "cosinesimil"   # 코사인 유사도
        },
        "number_of_shards": 1,
        "number_of_replicas": 2,            # 복제본 2개로 설정 (3개 AZ용 최적화)
        "analysis": {
            "analyzer": {
                "korean_analyzer": {        # nori 대신 사용자 정의 분석기
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
            # 레시피 기본 정보
            "recipe_id": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "korean_analyzer"},
            "ingredients": {"type": "text", "analyzer": "korean_analyzer"},
            "category": {"type": "keyword"},
            "cooking_method": {"type": "keyword"},
            "hashtag": {"type": "text", "analyzer": "korean_analyzer"},
            
            # AWS OpenSearch kNN 벡터 설정
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
            
            # 메타데이터
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    }
}

# 재료 인덱스 매핑 설정 (AWS OpenSearch kNN 방식)
ingredient_mapping = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
            "knn.space_type": "cosinesimil"
        },
        "number_of_shards": 1,
        "number_of_replicas": 2,            # 복제본 2개로 설정 (3개 AZ용 최적화)
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
            # 재료 기본 정보
            "ingredient_id": {"type": "long"},
            "name": {"type": "text", "analyzer": "korean_analyzer"},
            "aliases": {"type": "text", "analyzer": "korean_analyzer"},
            "category": {"type": "keyword"},
            
            # AWS OpenSearch kNN 벡터 설정
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
            
            # 메타데이터
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    }
}

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def test_connection():
    """
    AWS OpenSearch 서버와의 연결을 테스트합니다.
    
    Returns:
        bool: 연결 성공 시 True, 실패 시 False
    """
    try:
        info = client.info()
        print(f"✅ AWS OpenSearch 연결 성공!")
        print(f"   - 버전: {info['version']['number']}")
        print(f"   - 클러스터: {info['cluster_name']}")
        return True
    except Exception as e:
        print(f"❌ AWS OpenSearch 연결 실패: {e}")
        print(f"   - 호스트: {os.getenv('OPENSEARCH_HOST')}")
        print(f"   - 사용자명: {os.getenv('OPENSEARCH_USERNAME')}")
        return False

def delete_index_if_exists(index_name):
    """
    인덱스가 존재하면 삭제합니다.
    
    Args:
        index_name (str): 삭제할 인덱스명
    """
    try:
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"🗑️ 기존 인덱스 삭제: {index_name}")
            time.sleep(2)  # 삭제 완료 대기
    except Exception as e:
        print(f"⚠️ 인덱스 삭제 중 오류 (무시됨): {e}")

def create_index(index_name, mapping):
    """
    AWS OpenSearch에 인덱스를 생성합니다.
    
    Args:
        index_name (str): 생성할 인덱스 이름
        mapping (dict): 인덱스 매핑 설정
    
    Returns:
        bool: 생성 성공 시 True, 실패 시 False
    """
    try:
        # 기존 인덱스 삭제
        delete_index_if_exists(index_name)
        
        # 인덱스 생성
        response = client.indices.create(index=index_name, body=mapping)
        print(f"✅ 인덱스 생성 완료: {index_name}")
        
        # 인덱스 생성 완료 대기
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"❌ 인덱스 생성 실패 {index_name}: {e}")
        return False

def validate_embedding_data(data):
    """
    임베딩 데이터의 유효성을 검사합니다.
    
    Args:
        data (list): 검사할 데이터 리스트
    
    Returns:
        list: 유효한 데이터만 포함된 리스트
    """
    valid_data = []
    
    for item in data:
        embedding = item.get('embedding')
        
        # 임베딩이 존재하고 올바른 차원인지 확인
        if embedding and isinstance(embedding, list) and len(embedding) == 1536:
            # 모든 값이 숫자인지 확인
            if all(isinstance(x, (int, float)) for x in embedding):
                valid_data.append(item)
            else:
                print(f"⚠️ 임베딩 값이 숫자가 아님: {item.get('name', item.get('recipe_id', 'Unknown'))}")
        else:
            print(f"⚠️ 잘못된 임베딩 차원: {item.get('name', item.get('recipe_id', 'Unknown'))}")
    
    print(f"📊 유효한 데이터: {len(valid_data)}/{len(data)}")
    return valid_data

def preprocess_ingredient_data(ingredients):
    """
    재료 데이터를 AWS OpenSearch 업로드용으로 전처리합니다.
    
    Args:
        ingredients (list): 원본 재료 데이터 리스트
    
    Returns:
        list: 전처리된 재료 데이터 리스트
    """
    processed = []
    
    for ingredient in ingredients:
        # aliases 배열을 공백으로 구분된 문자열로 변환
        aliases = ingredient.get('aliases', [])
        if isinstance(aliases, list):
            aliases_text = ' '.join(str(alias) for alias in aliases)
        else:
            aliases_text = str(aliases)
        
        # AWS OpenSearch에 저장할 데이터 구조 생성
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
    """
    레시피 데이터를 전처리합니다.
    
    Args:
        recipes (list): 원본 레시피 데이터 리스트
    
    Returns:
        list: 전처리된 레시피 데이터 리스트
    """
    return recipes

def bulk_upload(index_name, data, batch_size=50):
    """
    대량의 데이터를 AWS OpenSearch에 배치 업로드합니다.
    벡터 데이터는 크기가 크므로 배치 사이즈를 줄입니다.
    
    Args:
        index_name (str): 업로드할 인덱스명
        data (list): 업로드할 데이터 리스트
        batch_size (int): 한 번에 처리할 문서 수 (기본값: 50, 벡터용으로 축소)
    
    Returns:
        bool: 모든 데이터 업로드 성공 시 True
    """
    actions = []
    total = len(data)
    success_count = 0
    
    print(f"📤 {index_name} 업로드 시작: {total}개 문서")
    
    for i, item in enumerate(data, 1):
        # 문서 ID 설정
        doc_id = None
        if 'recipe_id' in item:
            doc_id = item['recipe_id']
        elif 'ingredient_id' in item:
            doc_id = item['ingredient_id']
        
        # AWS OpenSearch 업로드 액션 생성
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
                # 대량 업로드 실행 (타임아웃 증가)
                response = helpers.bulk(
                    client, 
                    actions, 
                    timeout='600s',      # 10분 타임아웃 (벡터 업로드용)
                    max_retries=5,       # 최대 5번 재시도
                    initial_backoff=2,   # 초기 백오프 2초
                    max_backoff=600      # 최대 백오프 10분
                )
                
                # 성공한 업로드 수 계산
                success_count += len([r for r in response[1] if 'error' not in r.get('index', {})])
                
                # 진행률 출력
                print(f"   진행상황: {i}/{total} ({(i/total)*100:.1f}%) - 성공: {success_count}")
                
                actions = []
                time.sleep(1)  # API 부하 방지를 위한 대기
                
            except Exception as e:
                print(f"❌ 배치 업로드 오류: {e}")
                
                # 배치 업로드 실패 시 개별 업로드 시도
                for action in actions:
                    try:
                        client.index(
                            index=action["_index"], 
                            body=action["_source"], 
                            id=action.get("_id"),
                            timeout='300s'
                        )
                        success_count += 1
                    except Exception as individual_error:
                        print(f"   개별 업로드 실패: {individual_error}")
                        
                actions = []
    
    print(f"✅ {index_name} 업로드 완료: {success_count}/{total}")
    return success_count == total

def verify_upload():
    """
    업로드된 데이터를 검증합니다.
    """
    print("\n📋 업로드 결과 검증:")
    
    # 인덱싱 완료 대기
    time.sleep(5)
    
    # 레시피 인덱스 확인
    try:
        recipe_count = client.count(index=RECIPE_INDEX)["count"]
        print(f"   📊 레시피: {recipe_count}개")
        
        # 샘플 검색
        sample = client.search(
            index=RECIPE_INDEX, 
            body={"query": {"match_all": {}}, "size": 1}
        )
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
        
        # 샘플 검색
        sample = client.search(
            index=INGREDIENT_INDEX, 
            body={"query": {"match_all": {}}, "size": 1}
        )
        if sample["hits"]["hits"]:
            sample_ingredient = sample["hits"]["hits"][0]["_source"]
            print(f"   📝 샘플 재료: {sample_ingredient.get('name', 'N/A')}")
            print(f"   🏷️ 카테고리: {sample_ingredient.get('category', 'N/A')}")
            
    except Exception as e:
        print(f"   ❌ 재료 확인 실패: {e}")

def test_vector_search():
    """
    벡터 검색 기능을 테스트합니다.
    """
    print("\n🧪 벡터 검색 테스트:")
    
    try:
        # 더미 벡터로 검색 테스트
        dummy_vector = [0.1] * 1536  # 1536차원 더미 벡터
        
        search_body = {
            "size": 3,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": dummy_vector,
                        "k": 3
                    }
                }
            }
        }
        
        # 재료 검색 테스트
        response = client.search(index=INGREDIENT_INDEX, body=search_body)
        print(f"   ✅ 재료 벡터 검색 성공: {len(response['hits']['hits'])}개 결과")
        
        # 레시피 검색 테스트
        response = client.search(index=RECIPE_INDEX, body=search_body)
        print(f"   ✅ 레시피 벡터 검색 성공: {len(response['hits']['hits'])}개 결과")
        
    except Exception as e:
        print(f"   ❌ 벡터 검색 테스트 실패: {e}")

# ============================================================================
# 메인 실행 함수
# ============================================================================

def main():
    """
    메인 실행 함수
    """
    print("🚀 AWS OpenSearch 벡터 데이터 업로드 시작\n")
    
    # 1. 필수 환경변수 확인
    required_vars = ['OPENSEARCH_HOST']
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ {var} 환경변수가 설정되지 않았습니다")
            return
    
    # 인증 정보 확인
    if not (os.getenv('OPENSEARCH_USERNAME') and os.getenv('OPENSEARCH_PASSWORD')):
        if not os.getenv('AWS_REGION'):
            print("❌ 인증 정보가 부족합니다. Username/Password 또는 AWS 인증 설정이 필요합니다.")
            return
    
    # 2. AWS OpenSearch 연결 테스트
    if not test_connection():
        return
    
    # 3. 인덱스 생성
    print("\n📂 인덱스 생성:")
    if not create_index(RECIPE_INDEX, recipe_mapping):
        return
    if not create_index(INGREDIENT_INDEX, ingredient_mapping):
        return
    
    # 4. 데이터 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("\n📤 데이터 업로드:")
    
    # 5-1. 레시피 데이터 업로드
    recipe_files = [
        os.path.join(current_dir, "recipe_embeddings.json"),
        os.path.join(current_dir, "data", "recipe_embeddings.json"),
        "./recipe_embeddings.json"
    ]
    
    recipe_uploaded = False
    for recipe_file in recipe_files:
        if os.path.exists(recipe_file):
            print(f"📁 레시피 파일 로드: {recipe_file}")
            try:
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)
                
                # 데이터 유효성 검사
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
        os.path.join(current_dir, "ingredient_embeddings.json"),
        os.path.join(current_dir, "data", "ingredient_embeddings.json"),
        "./ingredient_embeddings.json"
    ]
    
    ingredient_uploaded = False
    for ingredient_file in ingredient_files:
        if os.path.exists(ingredient_file):
            print(f"📁 재료 파일 로드: {ingredient_file}")
            try:
                with open(ingredient_file, 'r', encoding='utf-8') as f:
                    ingredients = json.load(f)
                
                # 데이터 유효성 검사
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
    
    print("\n🎉 AWS OpenSearch 업로드 완료!")
    print("\n📖 다음 단계:")
    print("   1. AI 서버에서 kNN 검색 API 구현")
    print("   2. 네트워크 설정을 VPC로 복원 (보안 강화)")
    print("   3. 레시피 추천 시스템 통합 테스트")

# ============================================================================
# 스크립트 실행
# ============================================================================

if __name__ == "__main__":
    main()