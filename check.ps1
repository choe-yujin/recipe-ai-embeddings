# Recipe AI Project - 상태 확인
Write-Host "🔍 Recipe AI Project Status Check" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# OpenSearch 연결 확인
try {
    $health = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 5
    Write-Host "✅ OpenSearch: $($health.status)" -ForegroundColor Green
    
    # 데이터 확인
    try {
        $recipes = Invoke-RestMethod -Uri "http://localhost:9201/recipes/_count" -Method Get -TimeoutSec 5
        $ingredients = Invoke-RestMethod -Uri "http://localhost:9201/ingredients/_count" -Method Get -TimeoutSec 5
        Write-Host "📊 Recipes: $($recipes.count)" -ForegroundColor Green
        Write-Host "🥕 Ingredients: $($ingredients.count)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not fetch data counts" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ OpenSearch is not responding" -ForegroundColor Red
    Write-Host "💡 Try: docker-compose restart" -ForegroundColor Yellow
}

# 컨테이너 상태 확인
Write-Host "`n🐳 Docker Containers:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "opensearch"

Write-Host "`n🌐 Access URLs:" -ForegroundColor Cyan
Write-Host "   • OpenSearch API: http://localhost:9201" -ForegroundColor White
Write-Host "   • OpenSearch Dashboards: http://localhost:5601" -ForegroundColor White

Read-Host "`nPress Enter to continue"
