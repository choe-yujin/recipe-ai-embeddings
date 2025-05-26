import pymysql
import json
import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 환경변수에서 DB 설정 가져오기
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# 1. DB 연결
conn = pymysql.connect(**DB_CONFIG)

# 2. ingredients 테이블에서 id, name, category 조회
with conn.cursor() as cursor:
    cursor.execute("SELECT id, name, category FROM ingredients")
    ingredients = cursor.fetchall()

conn.close()

# 3. 동의어 사전 로드 (data/ingredient_aliases_nested.json)
with open("data/ingredient_aliases_nested.json", "r", encoding="utf-8") as f:
    alias_dict = json.load(f)

# 4. name과 category 기준으로 aliases 붙이기
output = []
for item in ingredients:
    std_name = item["name"]
    std_cat = item["category"]

    # 동의어 찾기
    aliases = alias_dict.get(std_cat, {}).get(std_name, [])

    output.append({
        "id": item["id"],
        "name": std_name,
        "aliases": aliases,
        "category": std_cat
    })

# 5. JSON 저장
os.makedirs("data", exist_ok=True)
with open("data/ingredient_embedding_input.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ ingredient_embedding_input.json 생성 완료: {len(output)}개 항목")
