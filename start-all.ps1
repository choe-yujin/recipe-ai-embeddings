# 전체 시스템 시작 스크립트
Write-Host "🚀 Recipe AI 시스템 전체 시작" -ForegroundColor Cyan
Write-Host "=" * 40 -ForegroundColor Cyan

# 1. recipe-ai-project OpenSearch 시작
Write-Host "`n1️⃣ recipe-ai-project OpenSearch 시작..." -ForegroundColor Yellow
Set-Location "C:\Users\User\AI\recipe-ai-project"

# OpenSearch 상태 확인
try {
    $response = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 5
    if ($response.status -eq "green" -or $response.status -eq "yellow") {
        Write-Host "✅ OpenSearch 이미 실행 중" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ OpenSearch 시작 중..." -ForegroundColor Yellow
    docker-compose up -d
    
    # OpenSearch 시작 대기
    Write-Host "⏳ OpenSearch 완전 시작 대기 (30초)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # 다시 확인
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 10
        Write-Host "✅ OpenSearch 시작 완료" -ForegroundColor Green
    } catch {
        Write-Host "❌ OpenSearch 시작 실패" -ForegroundColor Red
        Read-Host "Enter를 눌러 계속하거나 Ctrl+C로 중단"
    }
}

# 2. AI 서버 시작 안내
Write-Host "`n2️⃣ AI 서버 시작 준비..." -ForegroundColor Yellow
Set-Location "C:\Users\User\AI\ai-server"

Write-Host "📝 다음 명령어로 AI 서버를 시작하세요:" -ForegroundColor Cyan
Write-Host "   cd C:\Users\User\AI\ai-server" -ForegroundColor White
Write-Host "   uvicorn app.main:app --reload --port 8000" -ForegroundColor White

Write-Host "`n3️⃣ 테스트 방법:" -ForegroundColor Yellow
Write-Host "   python test_integration.py" -ForegroundColor White

Write-Host "`n🌐 접속 URL:" -ForegroundColor Cyan
Write-Host "   📊 OpenSearch: http://localhost:9201" -ForegroundColor White
Write-Host "   📈 Dashboard: http://localhost:5601" -ForegroundColor White
Write-Host "   🤖 AI 서버: http://localhost:8000" -ForegroundColor White
Write-Host "   📚 API 문서: http://localhost:8000/docs" -ForegroundColor White

Write-Host "`n✅ recipe-ai-project 준비 완료!" -ForegroundColor Green
Write-Host "이제 별도 터미널에서 AI 서버를 시작하세요." -ForegroundColor Yellow

Read-Host "`nEnter를 눌러 완료"
