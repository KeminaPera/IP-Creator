# Quick Build Script for IP-Creator Frontend
# Usage: .\build-frontend.ps1

Write-Host "🔨 Building frontend..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\frontend-vue"
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host "📦 Files written to: frontend-vue/dist/" -ForegroundColor Yellow
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot
