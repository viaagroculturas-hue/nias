# VIGÍA — Setup inicial (Windows PowerShell)
# Executar: .\setup.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "VIGIA — Setup" -ForegroundColor White
Write-Host "=============" -ForegroundColor DarkGray
Write-Host ""

# Verificar .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!] .env criado a partir de .env.example" -ForegroundColor Yellow
    Write-Host "    Preencha POSTGRES_PASSWORD, JWT_SECRET e ANTHROPIC_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# Frontend .env.local
if (-not (Test-Path "frontend\.env.local")) {
    Copy-Item "frontend\.env.local.example" "frontend\.env.local"
    Write-Host "[ok] frontend/.env.local criado" -ForegroundColor Green
}

# Verificar Docker
try {
    docker info | Out-Null
    Write-Host "[ok] Docker disponivel" -ForegroundColor Green
} catch {
    Write-Host "[!] Docker nao encontrado — instale Docker Desktop" -ForegroundColor Red
    exit 1
}

# Subir postgres e redis
Write-Host ""
Write-Host "Subindo PostgreSQL + Redis..." -ForegroundColor DarkGray
docker compose up -d postgres redis

Write-Host ""
Write-Host "Aguardando banco ficar pronto..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5

# Instalar deps frontend
Write-Host ""
Write-Host "Instalando dependencias frontend..." -ForegroundColor DarkGray
Set-Location frontend
npm install --silent
Set-Location ..

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Setup concluido. Para rodar:" -ForegroundColor White
Write-Host ""
Write-Host "  Terminal 1 (backend):" -ForegroundColor DarkGray
Write-Host "    cd backend && pip install -r requirements.txt" -ForegroundColor White
Write-Host "    uvicorn main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "  Terminal 2 (frontend):" -ForegroundColor DarkGray
Write-Host "    cd frontend && npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "  Terminal 3 (workers Celery):" -ForegroundColor DarkGray
Write-Host "    cd backend && celery -A tasks.celery_app worker -l info" -ForegroundColor White
Write-Host ""
Write-Host "  O seed roda automaticamente no primeiro boot." -ForegroundColor DarkGray
Write-Host "  Acompanhe em: http://localhost:3000" -ForegroundColor White
Write-Host "  API docs em:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor DarkGray
