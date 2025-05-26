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
    "charset": "utf8mb4"
}

# 1. DB 연결
conn = pymysql.connect(
    **DB_CONFIG,
    cursorclass=pymysql.cursors.DictCursor
)

# 2. 레시피 + 재료 JOIN → 주재료/부재료 구분
sql = """
SELECT
    r.rcp_seq AS recipe_id,
    r.rcp_nm AS recipe_name,
    GROUP_CONCAT(i.name ORDER BY i.name SEPARATOR ', ') AS processed_ingredients,
    r.rcp_category,
    r.rcp_way2,
    r.hash_tag
FROM recipes r
LEFT JOIN recipe_ingredients ri ON r.rcp_seq = ri.recipe_id
LEFT JOIN ingredients i ON ri.ingredient_id = i.id
GROUP BY r.rcp_seq, r.rcp_nm, r.rcp_category, r.rcp_way2, r.hash_tag
"""

with conn.cursor() as cursor:
    cursor.execute(sql)
    recipes = cursor.fetchall()

conn.close()

# 3. JSON 저장
os.makedirs("data", exist_ok=True)
with open("data/recipe_embedding_input.json", "w", encoding="utf-8") as f:
    json.dump(recipes, f, ensure_ascii=False, indent=2)

print(f"recipe_embedding_input.json 생성 완료: {len(recipes)}개 레시피")
