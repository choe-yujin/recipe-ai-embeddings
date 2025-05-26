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
INPUT_FILE = os.path.join(BASE_DIR, "data", "recipe_embedding_input.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "recipe_embeddings.json")
MODEL = "text-embedding-3-small"  # 1536차원 벡터

# API 요청 간 딜레이 (초)
REQUEST_DELAY = 0.5
# 최대 재시도 횟수
MAX_RETRIES = 3
# 재시도 간 딜레이 (초)
RETRY_DELAY = 5

def create_embedding_text(recipe):
    """임베딩용 텍스트 생성 (레시피 핵심 정보 조합)"""
    return f"""
레시피명: {recipe['recipe_name']}
재료: {recipe['processed_ingredients']}
조리법: {recipe['rcp_way2']}
카테고리: {recipe['rcp_category']}
해시태그: {recipe['hash_tag']}
""".strip()

def generate_recipe_embeddings_file():
    """레시피 임베딩 생성 및 JSON 파일 저장"""

    # 1. 입력 파일 로드
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    output_data = []

    for i, recipe in enumerate(recipes):
        print(f"[{i+1}/{len(recipes)}] {recipe['recipe_name']} 처리 중...")

        # 2. 임베딩용 텍스트 생성
        text = create_embedding_text(recipe)

        # 재시도 로직
        for retry in range(MAX_RETRIES):
            try:
                # 3. OpenAI Embedding API 호출
                response = client.embeddings.create(
                    input=text,
                    model=MODEL
                )
                embedding = response.data[0].embedding

                # 4. 저장할 구조
                doc = {
                    "recipe_id": recipe["recipe_id"],
                    "name": recipe["recipe_name"],
                    "embedding": embedding,
                    "ingredients": recipe["processed_ingredients"],
                    "category": recipe["rcp_category"],
                    "cooking_method": recipe["rcp_way2"],
                    "hashtag": recipe["hash_tag"],
                    "embedding_text": text,
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
                        print(f"최대 재시도 횟수 초과: {recipe['recipe_id']} - {e}")
                else:
                    print(f"오류 발생: {recipe['recipe_id']} - {e}")
                    break

    # 5. JSON 파일로 저장
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(output_data)}개 레시피 임베딩 생성 완료!")
    print(f"저장 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_recipe_embeddings_file()
