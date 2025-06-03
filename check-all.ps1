# 전체 시스템 상태 확인 스크립트
Write-Host "🔍 Recipe AI 시스템 전체 상태 확인" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# 1. recipe-ai-project OpenSearch 확인
Write-Host "`n📊 recipe-ai-project OpenSearch:" -ForegroundColor Yellow
try {
    $osResponse = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 5
    Write-Host "   ✅ 연결: 성공" -ForegroundColor Green
    Write-Host "   📈 상태: $($osResponse.status)" -ForegroundColor Green
    
    # 데이터 확인
    try {
        $recipes = Invoke-RestMethod -Uri "http://localhost:9201/recipes/_count" -Method Get -TimeoutSec 5
        $ingredients = Invoke-RestMethod -Uri "http://localhost:9201/ingredients/_count" -Method Get -TimeoutSec 5
        Write-Host "   📊 레시피: $($recipes.count)개" -ForegroundColor Green
        Write-Host "   🥕 재료: $($ingredients.count)개" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️ 데이터 확인 실패" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ 연결: 실패" -ForegroundColor Red
    Write-Host "   💡 해결: .\start-all.ps1 실행" -ForegroundColor Yellow
}

# 2. AI 서버 확인
Write-Host "`n🤖 AI 서버 (FastAPI):" -ForegroundColor Yellow
try {
    $aiResponse = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
    Write-Host "   ✅ 연결: 성공" -ForegroundColor Green
    Write-Host "   🔗 OpenSearch 연동: $($aiResponse.opensearch.connected ? '✅' : '❌')" -ForegroundColor $(if($aiResponse.opensearch.connected) {"Green"} else {"Red"})
    Write-Host "   ⚡ 기능: 벡터검색, OCR, 추천" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 연결: 실패" -ForegroundColor Red
    Write-Host "   💡 해결: uvicorn app.main:app --reload --port 8000" -ForegroundColor Yellow
}

# 3. 빠른 기능 테스트
Write-Host "`n⚡ 빠른 기능 테스트:" -ForegroundColor Yellow
try {
    $testResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/integration/recipes/search/text?q=볶음&limit=2" -Method Get -TimeoutSec 10
    Write-Host "   ✅ 텍스트 검색: $($testResponse.total)개 결과" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 텍스트 검색: 실패" -ForegroundColor Red
}

# 4. 접속 URL 안내
Write-Host "`n🌐 접속 URL:" -ForegroundColor Cyan
Write-Host "   📊 OpenSearch: http://localhost:9201" -ForegroundColor White
Write-Host "   📈 Dashboard: http://localhost:5601" -ForegroundColor White
Write-Host "   🤖 AI 서버: http://localhost:8000" -ForegroundColor White
Write-Host "   📚 API 문서: http://localhost:8000/docs" -ForegroundColor White

# 5. 종합 상태
Write-Host "`n🎯 종합 상태:" -ForegroundColor Cyan
$osOk = try { (Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -TimeoutSec 3).status -eq "green" } catch { $false }
$aiOk = try { (Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3).status -eq "healthy" } catch { $false }

if ($osOk -and $aiOk) {
    Write-Host "   🎉 모든 시스템 정상 작동!" -ForegroundColor Green
    Write-Host "   ✅ Java 백엔드 연동 준비 완료" -ForegroundColor Green
} elseif ($osOk) {
    Write-Host "   ⚠️ OpenSearch는 정상, AI 서버 시작 필요" -ForegroundColor Yellow
} elseif ($aiOk) {
    Write-Host "   ⚠️ AI 서버는 정상, OpenSearch 시작 필요" -ForegroundColor Yellow
} else {
    Write-Host "   ❌ 두 시스템 모두 시작 필요" -ForegroundColor Red
    Write-Host "   🚀 실행: .\start-all.ps1" -ForegroundColor Yellow
}

Read-Host "`nEnter를 눌러 완료"
