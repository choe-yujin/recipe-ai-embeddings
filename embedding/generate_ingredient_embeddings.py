import json
import openai
from datetime import datetime
import os
from openai import OpenAI
from dotenv import load_dotenv
import time

# .env 파일에서 환경변수 로드
load_dotenv()

# OpenAI API 키 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 절대 경로로 수정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "ingredient_embedding_input.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "ingredient_embeddings.json")
MODEL = "text-embedding-3-small"  # 1536차원 벡터

# API 요청 간 딜레이 (초)
REQUEST_DELAY = 0.5
# 최대 재시도 횟수
MAX_RETRIES = 3
# 재시도 간 딜레이 (초)
RETRY_DELAY = 5

def create_ingredient_embedding_text(ingredient):
    """식재료 임베딩용 텍스트 생성"""
    name = ingredient['name']
    aliases = ", ".join(ingredient.get("aliases", []))
    category = ingredient.get("category", "기타")

    return f"{name} ({aliases}) / {category}".strip()

def generate_ingredient_embeddings_file():
    """식재료 벡터 임베딩 생성 및 파일 저장"""

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)

    output_data = []

    for i, item in enumerate(ingredients):
        print(f"[{i+1}/{len(ingredients)}] {item['name']} 처리 중...")

        embedding_text = create_ingredient_embedding_text(item)

        # 재시도 로직
        for retry in range(MAX_RETRIES):
            try:
                response = client.embeddings.create(
                    input=embedding_text,
                    model=MODEL
                )
                embedding = response.data[0].embedding

                doc = {
                    "ingredient_id": item["id"],
                    "name": item["name"],
                    "aliases": item.get("aliases", []),
                    "category": item.get("category", "기타"),
                    "embedding": embedding,
                    "embedding_text": embedding_text,
                    "created_at": datetime.now().isoformat()
                }

                output_data.append(doc)
                
                # 성공적으로 처리된 경우 딜레이 후 다음 요청
                time.sleep(REQUEST_DELAY)
                break

            except Exception as e:
                if "rate limit" in str(e).lower():
                    if retry < MAX_RETRIES - 1:
                        print(f"Rate limit 도달. {RETRY_DELAY}초 후 재시도... (시도 {retry + 1}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"최대 재시도 횟수 초과: {item['name']} - {e}")
                else:
                    print(f"오류: {item['name']} - {e}")
                    break

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(output_data)}개 식재료 임베딩 완료!")
    print(f"저장 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_ingredient_embeddings_file()
