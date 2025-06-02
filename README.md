# Recipe AI Project

🍳 AI 기반 레시피 추천 시스템 with OpenSearch & Korean NLP

## 🚀 신규 팀원 - 원클릭 설치

```bash
git clone <repository-url>
cd recipe-ai-project
.\setup.ps1
```

**끝!** 2-3분 기다리면 모든 것이 자동으로 설치됩니다.

## 🔧 개발자 명령어

```bash
.\check.ps1     # 상태 확인
.\clean.ps1     # 완전 초기화 후 재설치

# 수동 조작
docker-compose restart                              # 재시작
python scripts/upload_to_opensearch_local.py      # 데이터 재업로드
```

## 🌐 접속 URL

- **OpenSearch API**: http://localhost:9201
- **OpenSearch Dashboards**: http://localhost:5601

## ⚙️ 환경 설정

`.env` 파일에서 OpenAI API 키 설정:
```env
OPENAI_API_KEY=your_api_key_here
```

## 📁 프로젝트 구조

```
recipe-ai-project/
├── README.md              # 이 파일
├── setup.ps1              # 원클릭 설치
├── check.ps1              # 상태 확인  
├── clean.ps1              # 완전 초기화
├── docker-compose.yml     # OpenSearch 설정
├── Dockerfile            # Nori 플러그인 포함
├── requirements.txt       # Python 의존성
├── .env.example          # 환경 변수 템플릿
├── app/                  # AI 서버 (FastAPI)
├── data/                 # 벡터 임베딩 데이터
├── scripts/              # 데이터 업로드 스크립트
└── embedding/            # 임베딩 생성 스크립트
```

## 🔍 기술 스택

- **OpenSearch**: 벡터 검색 + 한국어 분석 (Nori)
- **OpenAI**: 텍스트 임베딩 생성  
- **FastAPI**: AI 서버
- **Docker**: 컨테이너화

## 🚨 문제 해결

뭔가 안 되면:
```bash
.\clean.ps1     # 모든 것 삭제
.\setup.ps1     # 다시 설치
```
