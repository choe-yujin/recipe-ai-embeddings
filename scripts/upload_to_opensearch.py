# ============================================================================
# OpenSearch 데이터 업로드 스크립트
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
    OpenSearch 클라이언트를 생성합니다.
    
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
            timeout=30,                      # 연결 타임아웃 30초
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
                timeout=30,
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
# 인덱스 설정 및 매핑 정의
# ============================================================================

# 인덱스 이름 상수 정의
RECIPE_INDEX = 'recipes'        # 레시피 인덱스명
INGREDIENT_INDEX = 'ingredients' # 재료 인덱스명

# 레시피 인덱스 매핑 설정
recipe_mapping = {
    "mappings": {
        "properties": {
            # 레시피 기본 정보
            "recipe_id": {"type": "keyword"},                    # 레시피 고유 ID (정확 매칭용)
            "name": {"type": "text", "analyzer": "nori"},        # 레시피명 (한국어 형태소 분석)
            "ingredients": {"type": "text", "analyzer": "nori"}, # 재료 목록 (검색 가능)
            "category": {"type": "keyword"},                     # 카테고리 (필터링용)
            "cooking_method": {"type": "keyword"},               # 조리 방법 (필터링용)
            "hashtag": {"type": "text", "analyzer": "nori"},     # 해시태그 (검색 가능)
            
            # 벡터 임베딩 (AI 추천의 핵심)
            "embedding": {
                "type": "dense_vector",    # 벡터 타입
                "dims": 1536,              # OpenAI text-embedding-3-small 차원수
                "index": True,             # 벡터 인덱싱 활성화
                "similarity": "cosine"     # 코사인 유사도 사용
            },
            
            # 메타데이터
            "embedding_text": {"type": "text"},  # 임베딩 생성에 사용된 원본 텍스트
            "created_at": {"type": "date"}       # 생성 날짜
        }
    },
    "settings": {
        "number_of_shards": 1,      # 단일 샤드 (소규모 데이터용)
        "number_of_replicas": 0,    # 복제본 없음 (단일 노드용)
        "analysis": {
            "analyzer": {
                "nori": {               # 한국어 형태소 분석기
                    "type": "nori",
                    # 불용어 태그 설정 (조사, 어미 등 제외)
                    "stoptags": ["E", "IC", "J", "MAG", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"]
                }
            }
        }
    }
}

# 재료 인덱스 매핑 설정
ingredient_mapping = {
    "mappings": {
        "properties": {
            # 재료 기본 정보
            "ingredient_id": {"type": "long"},                   # 재료 고유 ID
            "name": {"type": "text", "analyzer": "nori"},        # 재료명 (한국어 형태소 분석)
            "aliases": {"type": "text", "analyzer": "nori"},     # 동의어/별칭 (문자열로 변환됨)
            "category": {"type": "keyword"},                     # 재료 카테고리
            
            # 벡터 임베딩
            "embedding": {
                "type": "dense_vector",
                "dims": 1536,
                "index": True,
                "similarity": "cosine"
            },
            
            # 메타데이터
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "nori": {
                    "type": "nori",
                    "stoptags": ["E", "IC", "J", "MAG", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"]
                }
            }
        }
    }
}

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def test_connection():
    """
    OpenSearch 서버와의 연결을 테스트합니다.
    
    Returns:
        bool: 연결 성공 시 True, 실패 시 False
    """
    try:
        info = client.info()
        print(f"✅ OpenSearch 연결 성공!")
        print(f"   - 버전: {info['version']['number']}")
        print(f"   - 클러스터: {info['cluster_name']}")
        return True
    except Exception as e:
        print(f"❌ OpenSearch 연결 실패: {e}")
        print(f"   - 호스트: {os.getenv('OPENSEARCH_HOST')}")
        print(f"   - 사용자명: {os.getenv('OPENSEARCH_USERNAME')}")
        return False

def create_index(index_name, mapping):
    """
    OpenSearch에 인덱스를 생성합니다.
    
    Args:
        index_name (str): 생성할 인덱스 이름
        mapping (dict): 인덱스 매핑 설정
    
    Returns:
        bool: 생성 성공 시 True, 실패 시 False
    """
    try:
        # 인덱스가 이미 존재하는지 확인
        if not client.indices.exists(index=index_name):
            # 인덱스 생성
            client.indices.create(index=index_name, body=mapping)
            print(f"✅ 인덱스 생성 완료: {index_name}")
        else:
            print(f"ℹ️ 인덱스가 이미 존재합니다: {index_name}")
        return True
    except Exception as e:
        print(f"❌ 인덱스 생성 실패 {index_name}: {e}")
        return False

def preprocess_ingredient_data(ingredients):
    """
    재료 데이터를 OpenSearch 업로드용으로 전처리합니다.
    
    주요 작업:
    - aliases 배열을 문자열로 변환 (OpenSearch text 필드용)
    - 필요한 필드만 추출
    
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
            aliases_text = ' '.join(aliases)  # ['밀가루', '박력분'] → '밀가루 박력분'
        else:
            aliases_text = str(aliases)
        
        # OpenSearch에 저장할 데이터 구조 생성
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
    
    현재는 특별한 전처리가 필요없지만, 향후 확장을 위해 함수로 분리
    
    Args:
        recipes (list): 원본 레시피 데이터 리스트
    
    Returns:
        list: 전처리된 레시피 데이터 리스트
    """
    return recipes

def bulk_upload(index_name, data, batch_size=100):
    """
    대량의 데이터를 OpenSearch에 배치 업로드합니다.
    
    Args:
        index_name (str): 업로드할 인덱스명
        data (list): 업로드할 데이터 리스트
        batch_size (int): 한 번에 처리할 문서 수 (기본값: 100)
    
    Returns:
        bool: 모든 데이터 업로드 성공 시 True
    """
    actions = []           # 배치 업로드용 액션 리스트
    total = len(data)      # 전체 문서 수
    success_count = 0      # 성공한 업로드 수
    
    print(f"📤 {index_name} 업로드 시작: {total}개 문서")
    
    for i, item in enumerate(data, 1):
        # 문서 ID 설정 (고유 식별자)
        doc_id = None
        if 'recipe_id' in item:
            doc_id = item['recipe_id']
        elif 'ingredient_id' in item:
            doc_id = item['ingredient_id']
        
        # OpenSearch 업로드 액션 생성
        action = {
            "_index": index_name,    # 인덱스명
            "_source": item          # 실제 데이터
        }
        
        # 문서 ID가 있으면 설정 (중복 방지)
        if doc_id:
            action["_id"] = doc_id
            
        actions.append(action)
        
        # 배치 크기에 도달하거나 마지막 문서인 경우 업로드 실행
        if len(actions) >= batch_size or i == total:
            try:
                # 대량 업로드 실행
                response = helpers.bulk(
                    client, 
                    actions, 
                    timeout='300s',      # 5분 타임아웃
                    max_retries=3        # 최대 3번 재시도
                )
                
                # 성공한 업로드 수 계산
                success_count += len([r for r in response[1] if 'error' not in r.get('index', {})])
                
                # 진행률 출력
                print(f"   진행상황: {i}/{total} ({(i/total)*100:.1f}%)")
                
                actions = []  # 액션 리스트 초기화
                time.sleep(0.1)  # API 부하 방지를 위한 짧은 대기
                
            except Exception as e:
                print(f"❌ 배치 업로드 오류: {e}")
                
                # 배치 업로드 실패 시 개별 업로드 시도
                for action in actions:
                    try:
                        client.index(
                            index=action["_index"], 
                            body=action["_source"], 
                            id=action.get("_id")
                        )
                        success_count += 1
                    except:
                        pass  # 개별 업로드도 실패하면 무시
                actions = []
    
    print(f"✅ {index_name} 업로드 완료: {success_count}/{total}")
    return success_count == total

def verify_upload():
    """
    업로드된 데이터를 검증합니다.
    
    - 각 인덱스의 문서 수 확인
    - 샘플 데이터 조회
    - 임베딩 차원수 확인
    """
    print("\n📋 업로드 결과 검증:")
    
    # 레시피 인덱스 문서 수 확인
    try:
        recipe_count = client.count(index=RECIPE_INDEX)["count"]
        print(f"   레시피: {recipe_count}개")
    except Exception as e:
        print(f"   레시피 확인 실패: {e}")
    
    # 재료 인덱스 문서 수 확인
    try:
        ingredient_count = client.count(index=INGREDIENT_INDEX)["count"]
        print(f"   재료: {ingredient_count}개")
    except Exception as e:
        print(f"   재료 확인 실패: {e}")
    
    # 샘플 데이터 조회 및 임베딩 차원수 확인
    try:
        sample = client.search(
            index=INGREDIENT_INDEX, 
            body={"query": {"match_all": {}}, "size": 1}
        )
        if sample["hits"]["hits"]:
            sample_item = sample["hits"]["hits"][0]["_source"]
            print(f"   샘플 재료: {sample_item.get('name', 'N/A')}")
            print(f"   임베딩 차원: {len(sample_item.get('embedding', []))}")
    except Exception as e:
        print(f"   샘플 검색 실패: {e}")

# ============================================================================
# 메인 실행 함수
# ============================================================================

def main():
    """
    메인 실행 함수
    
    실행 순서:
    1. 환경변수 확인
    2. OpenSearch 연결 테스트
    3. 인덱스 생성
    4. 데이터 로드 및 전처리
    5. 대량 업로드 실행
    6. 결과 검증
    """
    print("🚀 OpenSearch 데이터 업로드 시작\n")
    
    # 1. 필수 환경변수 확인
    required_vars = ['OPENSEARCH_HOST']
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ {var} 환경변수가 설정되지 않았습니다")
            return
    
    # Username/Password 또는 AWS 인증 중 하나는 있어야 함
    if not (os.getenv('OPENSEARCH_USERNAME') and os.getenv('OPENSEARCH_PASSWORD')):
        if not os.getenv('AWS_REGION'):
            print("❌ 인증 정보가 부족합니다. Username/Password 또는 AWS 인증 설정이 필요합니다.")
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
    
    # 인덱스 생성 완료 대기
    time.sleep(2)
    
    # 4. 데이터 파일 경로 설정
    # 프로젝트 구조에 따라 경로 조정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("\n📤 데이터 업로드:")
    
    # 5-1. 레시피 데이터 업로드
    recipe_file = os.path.join(base_dir, "data", "recipe_embeddings.json")
    if os.path.exists(recipe_file):
        print(f"📁 레시피 파일 로드: {recipe_file}")
        with open(recipe_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        
        # 전처리 및 업로드
        processed_recipes = preprocess_recipe_data(recipes)
        bulk_upload(RECIPE_INDEX, processed_recipes)
    else:
        print(f"❌ 레시피 파일을 찾을 수 없습니다: {recipe_file}")
        print(f"   현재 경로에서 찾아보세요: ./recipe_embeddings.json")
    
    # 5-2. 재료 데이터 업로드
    ingredient_file = os.path.join(base_dir, "data", "ingredient_embeddings.json")
    if os.path.exists(ingredient_file):
        print(f"📁 재료 파일 로드: {ingredient_file}")
        with open(ingredient_file, 'r', encoding='utf-8') as f:
            ingredients = json.load(f)
        
        # 전처리 및 업로드 (aliases 배열 → 문자열 변환)
        processed_ingredients = preprocess_ingredient_data(ingredients)
        bulk_upload(INGREDIENT_INDEX, processed_ingredients)
    else:
        print(f"❌ 재료 파일을 찾을 수 없습니다: {ingredient_file}")
        print(f"   현재 경로에서 찾아보세요: ./ingredient_embeddings.json")
    
    # 6. 인덱싱 완료 대기
    print("\n⏳ 인덱싱 완료 대기 중...")
    time.sleep(5)
    
    # 7. 업로드 결과 검증
    verify_upload()
    
    print("\n🎉 모든 작업이 완료되었습니다!")
    print("\n📖 다음 단계:")
    print("   1. AI 서버에서 벡터 검색 테스트")
    print("   2. 네트워크 설정을 VPC로 복원 (보안 강화)")
    print("   3. 레시피 추천 API 개발")

# ============================================================================
# 스크립트 실행
# ============================================================================

if __name__ == "__main__":
    main()