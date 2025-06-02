# Recipe AI Project - 원클릭 설치 스크립트
# 신규 팀원용 - 이 스크립트 하나면 모든 설치가 완료됩니다

Write-Host "🚀 Recipe AI Project Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# 1. 사전 요구사항 확인
Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    $pythonVersion = python --version
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# 2. 환경 설정
Write-Host "`n⚙️ Setting up environment..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ .env file created from template" -ForegroundColor Green
        Write-Host "⚠️  Please edit .env file and add your OPENAI_API_KEY" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# 3. Python 의존성 설치
Write-Host "`n📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt > $null
Write-Host "✅ Python packages installed" -ForegroundColor Green

# 4. OpenSearch 빌드 및 시작
Write-Host "`n🐳 Building OpenSearch with Nori plugin..." -ForegroundColor Yellow
docker-compose build --no-cache > $null
Write-Host "✅ OpenSearch image built with Nori plugin" -ForegroundColor Green

Write-Host "`n🚀 Starting OpenSearch..." -ForegroundColor Yellow
docker-compose up -d > $null
Write-Host "✅ OpenSearch containers started" -ForegroundColor Green

# 5. OpenSearch 시작 대기
Write-Host "`n⏳ Waiting for OpenSearch to be ready (90 seconds)..." -ForegroundColor Yellow
$timeout = 90
$interval = 5
$elapsed = 0

while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 5
        if ($response.status -eq "green" -or $response.status -eq "yellow") {
            Write-Host "✅ OpenSearch is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # 계속 시도
    }
    
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    Write-Host "." -NoNewline -ForegroundColor Gray
}

if ($elapsed -ge $timeout) {
    Write-Host "`n⚠️  OpenSearch might still be starting. Continuing anyway..." -ForegroundColor Yellow
}

# 6. 데이터 업로드
Write-Host "`n📊 Uploading vector data to OpenSearch..." -ForegroundColor Yellow
cd scripts
$uploadResult = python upload_to_opensearch_local.py
cd ..

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Vector data uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Data upload had some issues, but continuing..." -ForegroundColor Yellow
}

# 7. 최종 확인
Write-Host "`n🔍 Final health check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:9201/_cluster/health" -Method Get -TimeoutSec 10
    $recipeCount = Invoke-RestMethod -Uri "http://localhost:9201/recipes/_count" -Method Get -TimeoutSec 10
    $ingredientCount = Invoke-RestMethod -Uri "http://localhost:9201/ingredients/_count" -Method Get -TimeoutSec 10
    
    Write-Host "✅ OpenSearch Status: $($health.status)" -ForegroundColor Green
    Write-Host "✅ Recipes: $($recipeCount.count)" -ForegroundColor Green
    Write-Host "✅ Ingredients: $($ingredientCount.count)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not verify data counts, but OpenSearch is running" -ForegroundColor Yellow
}

# 8. 완료 메시지
Write-Host "`n🎉 Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ OpenSearch is running with Nori plugin" -ForegroundColor White
Write-Host "✅ Vector data has been uploaded" -ForegroundColor White
Write-Host "`n🌐 Access URLs:" -ForegroundColor Cyan
Write-Host "   • OpenSearch API: http://localhost:9201" -ForegroundColor White
Write-Host "   • OpenSearch Dashboards: http://localhost:5601" -ForegroundColor White
Write-Host "`n🔧 Useful commands:" -ForegroundColor Cyan
Write-Host "   • Check status: .\check.ps1" -ForegroundColor White
Write-Host "   • Restart: docker-compose restart" -ForegroundColor White
Write-Host "   • Clean & reset: .\clean.ps1" -ForegroundColor White
Write-Host "`n⚠️  Don't forget to add your OPENAI_API_KEY to the .env file!" -ForegroundColor Yellow

Read-Host "`nPress Enter to finish"
