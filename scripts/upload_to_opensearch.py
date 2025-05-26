import json
import os
from opensearchpy import OpenSearch, helpers
from dotenv import load_dotenv
import time

# .env 파일에서 환경변수 로드
load_dotenv()

# OpenSearch 클라이언트 설정
client = OpenSearch(
    hosts=[{'host': os.getenv('OPENSEARCH_HOST', 'localhost'), 'port': 9200}],
    http_auth=(os.getenv('OPENSEARCH_USER', 'admin'), os.getenv('OPENSEARCH_PASSWORD', 'admin')),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

# 인덱스 설정
RECIPE_INDEX = 'recipes'
INGREDIENT_INDEX = 'ingredients'

# 인덱스 매핑 설정
recipe_mapping = {
    "mappings": {
        "properties": {
            "recipe_id": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "korean"},
            "ingredients": {"type": "text", "analyzer": "korean"},
            "category": {"type": "keyword"},
            "cooking_method": {"type": "keyword"},
            "hashtag": {"type": "text", "analyzer": "korean"},
            "embedding": {"type": "knn_vector", "dimension": 1536},
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    },
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100
        }
    }
}

ingredient_mapping = {
    "mappings": {
        "properties": {
            "ingredient_id": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "korean"},
            "aliases": {"type": "text", "analyzer": "korean"},
            "category": {"type": "keyword"},
            "embedding": {"type": "knn_vector", "dimension": 1536},
            "embedding_text": {"type": "text"},
            "created_at": {"type": "date"}
        }
    },
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100
        }
    }
}

def create_index(index_name, mapping):
    """인덱스 생성"""
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=mapping)
        print(f"인덱스 생성 완료: {index_name}")
    else:
        print(f"인덱스가 이미 존재합니다: {index_name}")

def bulk_upload(index_name, data, batch_size=100):
    """벌크 업로드"""
    actions = []
    total = len(data)
    
    for i, item in enumerate(data, 1):
        action = {
            "_index": index_name,
            "_source": item
        }
        actions.append(action)
        
        if len(actions) >= batch_size or i == total:
            try:
                helpers.bulk(client, actions)
                print(f"[{i}/{total}] {index_name} 데이터 업로드 중...")
                actions = []
                time.sleep(0.1)  # API 부하 방지
            except Exception as e:
                print(f"오류 발생: {e}")
                return False
    
    return True

def main():
    # 인덱스 생성
    create_index(RECIPE_INDEX, recipe_mapping)
    create_index(INGREDIENT_INDEX, ingredient_mapping)
    
    # 데이터 로드
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 레시피 데이터 업로드
    recipe_file = os.path.join(base_dir, "data", "recipe_embeddings.json")
    if os.path.exists(recipe_file):
        with open(recipe_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        if bulk_upload(RECIPE_INDEX, recipes):
            print(f"레시피 데이터 업로드 완료: {len(recipes)}개")
    
    # 재료 데이터 업로드
    ingredient_file = os.path.join(base_dir, "data", "ingredient_embeddings.json")
    if os.path.exists(ingredient_file):
        with open(ingredient_file, 'r', encoding='utf-8') as f:
            ingredients = json.load(f)
        if bulk_upload(INGREDIENT_INDEX, ingredients):
            print(f"재료 데이터 업로드 완료: {len(ingredients)}개")

if __name__ == "__main__":
    main() 