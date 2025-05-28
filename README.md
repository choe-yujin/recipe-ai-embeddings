# 레시피 AI 임베딩 프로젝트

이 프로젝트는 레시피 데이터를 벡터 임베딩하여 OpenSearch 기반의 AI 레시피 검색 시스템을 구축합니다.

## 주요 기능

- MySQL 레시피 데이터 추출
- OpenAI API를 활용한 레시피/재료 벡터 임베딩
- OpenSearch 기반 벡터 검색 시스템 구축
- 한국어 자연어 처리 지원

## 프로젝트 구조

```
recipe-ai-project/
├── data/                      # 데이터 파일 저장 디렉토리
│   ├── ingredient_aliases_nested.json  # 재료 동의어 사전
│   ├── recipe_embedding_input.json     # 레시피 임베딩 입력 데이터
│   ├── ingredient_embedding_input.json # 재료 임베딩 입력 데이터
│   ├── recipe_embeddings.json          # 레시피 임베딩 결과
│   └── ingredient_embeddings.json      # 재료 임베딩 결과
├── embedding/                 # 임베딩 생성 스크립트
│   ├── generate_recipe_embeddings.py    # 레시피 임베딩 생성
│   └── generate_ingredient_embeddings.py # 재료 임베딩 생성
├── scripts/                   # 데이터 처리 스크립트
│   ├── export_recipe_embedding_input.py    # 레시피 데이터 추출
│   ├── export_ingredient_embedding_input.py # 재료 데이터 추출
│   └── upload_to_opensearch.py            # OpenSearch 업로드
├── .env                      # 환경 변수 설정 파일
├── .env.example              # 환경 변수 예시 파일
└── requirements.txt          # 프로젝트 의존성 파일
```

## 설치 방법

1. Python 3.10 이상 설치

2. 가상환경 생성 및 활성화
```bash
conda create -n recipe-embed python=3.10
conda activate recipe-embed
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
- `.env.example` 파일을 `.env`로 복사
- 다음 환경 변수들을 설정:
  ```
  # 데이터베이스 설정
  DB_HOST=localhost
  DB_USER=your_username
  DB_PASSWORD=your_password
  DB_NAME=recipe_go

  # OpenAI API 설정
  OPENAI_API_KEY=your_openai_api_key

  # OpenSearch 설정
  OPENSEARCH_HOST=your_host
  ```

## 사용 방법

1. 데이터 추출
```bash
cd scripts
python export_recipe_embedding_input.py
python export_ingredient_embedding_input.py
```

2. 벡터 임베딩 생성
```bash
cd embedding
python generate_recipe_embeddings.py
python generate_ingredient_embeddings.py
```

3. OpenSearch 업로드
```bash
cd scripts
python upload_to_opensearch.py
```

## 기술 스택

- Python 3.10
- MySQL
- OpenAI API (text-embedding-3-small)
- OpenSearch
- 한국어 자연어 처리

## 주의사항

1. OpenAI API 사용량
   - API 호출 시 rate limit에 주의
   - 충분한 할당량이 있는지 확인
   - 결제 정보 설정 필요

2. 데이터 파일
   - `data/` 디렉토리의 JSON 파일들은 Git에서 추적되지 않음
   - 필요한 경우 수동으로 백업 필요

3. OpenSearch 설정
   - AWS OpenSearch Service 사용 시:
     - 도메인 생성 시 "Custom endpoint" 옵션 선택
     - 보안 설정에서 "Fine-grained access control" 활성화
     - 노드 유형은 최소 2개 이상 권장 (t3.small.search 이상)
     - KNN 벡터 검색을 위한 플러그인 자동 설치됨
     - Nori 한국어 분석기 기본 제공됨
   - 로컬 OpenSearch 사용 시:
     - OpenSearch 2.x 이상 버전 설치
     - KNN 플러그인 수동 설치 필요
     - Nori 플러그인 수동 설치 필요
   - 인덱스 설정:
     ```json
     {
       "settings": {
         "analysis": {
           "analyzer": {
             "korean": {
               "tokenizer": "nori_tokenizer",
               "filter": ["nori_readingform", "nori_part_of_speech"]
             }
           }
         }
       }
     }
     ```

## AWS OpenSearch Service 설정 가이드

### 1. 도메인 생성

1. AWS 콘솔에서 OpenSearch Service로 이동
2. "Create domain" 클릭
3. 기본 설정:
   - Domain name: `recipe-search` (원하는 이름)
   - Deployment type: `Production`
   - Version: `OpenSearch 2.11` (또는 최신 버전)
   - Instance type: `t3.small.search` (최소 2개 이상)
   - Number of nodes: `2` (최소 권장)

### 2. 네트워크 설정

1. VPC 선택:
   - "VPC access" 선택
   - 기존 VPC 선택 또는 새로 생성
   - 보안 그룹 설정 (필요한 포트: 443)

2. 엔드포인트 설정:
   - "Custom endpoint" 활성화
   - 엔드포인트 이름 설정 (예: `recipe-search-endpoint`)

### 3. 보안 설정

1. IAM 인증 설정:
   - "Enable IAM authentication" 활성화
   - IAM 역할 생성 및 필요한 권한 부여
   - OpenSearch 도메인에 대한 접근 권한 설정

2. AWS 자격 증명 설정:
   - AWS CLI 설정 파일(~/.aws/credentials)에 자격 증명 추가
   - 또는 환경 변수로 설정:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=ap-northeast-2
   ```

### 4. 환경 변수 설정

`.env` 파일에 다음 설정 추가:
```
OPENSEARCH_HOST=your-custom-endpoint.region.es.amazonaws.com
```

### 5. 인덱스 생성

도메인이 생성된 후, 다음 명령어로 인덱스 생성:

```bash
# 레시피 인덱스 생성
curl -X PUT "https://${OPENSEARCH_HOST}/recipes" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "index": {
        "knn": true,
        "knn.algo_param.ef_search": 100
      },
      "analysis": {
        "analyzer": {
          "korean": {
            "tokenizer": "nori_tokenizer",
            "filter": ["nori_readingform", "nori_part_of_speech"]
          }
        }
      }
    },
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
    }
  }'

# 재료 인덱스 생성
curl -X PUT "https://${OPENSEARCH_HOST}/ingredients" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "index": {
        "knn": true,
        "knn.algo_param.ef_search": 100
      },
      "analysis": {
        "analyzer": {
          "korean": {
            "tokenizer": "nori_tokenizer",
            "filter": ["nori_readingform", "nori_part_of_speech"]
          }
        }
      }
    },
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
    }
  }'
```

### 6. 모니터링 설정

1. CloudWatch 통합:
   - 도메인 설정에서 CloudWatch 로깅 활성화
   - 주요 지표 모니터링:
     - CPU 사용률
     - 메모리 사용률
     - 디스크 사용률
     - 검색 지연 시간

2. 알람 설정:
   - CPU 사용률 80% 이상
   - 메모리 사용률 80% 이상
   - 디스크 사용률 80% 이상

### 7. 비용 최적화

1. 인스턴스 크기:
   - 초기에는 t3.small.search로 시작
   - 필요에 따라 스케일 업/다운

2. 스토리지:
   - EBS 볼륨 크기 최적화
   - 필요에 따라 스토리지 확장

3. 백업:
   - 자동 스냅샷 설정
   - 수동 스냅샷 정기적 생성

### 8. 문제 해결

1. 연결 문제:
   - VPC 보안 그룹 설정 확인
   - IAM 역할 권한 확인
   - 엔드포인트 DNS 확인

2. 성능 문제:
   - 인스턴스 크기 조정
   - 샤드 수 최적화
   - 인덱스 설정 조정

3. 비용 문제:
   - 사용하지 않는 인덱스 삭제
   - 오래된 데이터 아카이빙
   - 인스턴스 크기 최적화

## AWS 관리자 가이드

### 1. 프로젝트 설정

1. 프로젝트 클론
```bash
git clone [repository_url]
cd recipe-ai-project
```

2. Conda 환경 설정
```bash
# Conda 설치 (이미 설치되어 있다면 skip)
# Windows: https://docs.conda.io/en/latest/miniconda.html 에서 다운로드

# 가상환경 생성 및 활성화
conda create -n recipe-embed python=3.10
conda activate recipe-embed
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. AWS 콘솔 설정

1. IAM 사용자 생성 및 권한 설정
   - AWS 콘솔 로그인
   - IAM 서비스로 이동
   - "사용자" → "사용자 생성"
   - 사용자 이름 입력 (예: recipe-opensearch-admin)
   - "액세스 키 - 프로그래밍 방식 액세스" 선택
   - 필요한 권한 정책 연결:
     - `AmazonOpenSearchServiceFullAccess`
     - `AmazonOpenSearchServiceReadOnlyAccess`
   - 사용자 생성 완료 후 액세스 키와 시크릿 키 저장

2. 환경 변수 설정
```bash
# .env 파일 생성
copy .env.example .env

# .env 파일 편집
# 다음 내용만 설정:
OPENSEARCH_HOST=vpc-refrige-go-pomktvnaxb7w7sxhi74g26ujsq.ap-northeast-2.es.amazonaws.com
```

3. AWS 자격 증명을 환경 변수로 설정
```bash
# Windows PowerShell에서:
$env:AWS_ACCESS_KEY_ID="your_access_key"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$env:AWS_REGION="ap-northeast-2"
```

### 3. 데이터 업로드

1. 데이터 파일 확인
```bash
# data 디렉토리에 다음 파일들이 있는지 확인:
# - recipe_embeddings.json
# - ingredient_embeddings.json
```

2. 스크립트 실행
```bash
cd scripts
python upload_to_opensearch.py
```

### 4. 문제 해결

1. AWS 콘솔에서 확인사항:
   - OpenSearch 도메인이 생성되어 있는지 확인
   - OpenSearch 도메인의 엔드포인트 주소가 올바른지 확인
   - VPC 엔드포인트를 사용하는 경우, VPN이나 AWS Direct Connect가 설정되어 있는지 확인
   - 생성한 IAM 사용자의 권한이 올바르게 설정되어 있는지 확인

2. 문제 발생 시 확인사항:
   - AWS 자격 증명이 올바른지 확인
   - OpenSearch 호스트 주소가 올바른지 확인
   - 네트워크 연결 상태 확인
   - IAM 권한 확인

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
