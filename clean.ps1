# Recipe AI Project - 완전 초기화
Write-Host "🧹 Recipe AI Project Clean Reset" -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red
Write-Host "This will remove all Docker containers, images, and data!" -ForegroundColor Yellow

$confirm = Read-Host "Are you sure you want to continue? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Green
    exit 0
}

Write-Host "`n🗑️  Removing containers and volumes..." -ForegroundColor Yellow
docker-compose down -v --remove-orphans

Write-Host "🗑️  Removing images..." -ForegroundColor Yellow
docker rmi recipe-ai-project-opensearch --force 2>$null
docker rmi opensearchproject/opensearch:2.4.0 --force 2>$null
docker rmi opensearchproject/opensearch-dashboards:2.4.0 --force 2>$null

Write-Host "🗑️  Cleaning up Docker system..." -ForegroundColor Yellow
docker system prune -f

Write-Host "`n✅ Clean reset complete!" -ForegroundColor Green
Write-Host "💡 Run .\setup.ps1 to reinstall everything" -ForegroundColor Cyan

Read-Host "Press Enter to continue"
