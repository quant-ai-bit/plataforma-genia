# Script para iniciar PLATAFORMA GENIA Local (Backend + Frontend)

Write-Host "Iniciando Backend (FastAPI)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload"

Write-Host "Iniciando Frontend (Next.js Dashboard)..." -ForegroundColor Blue
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd dashboard; npm run dev -- -p 3002"

Write-Host "Todo listo. El Dashboard abrirá en http://localhost:3002 y el Backend en http://localhost:8000" -ForegroundColor Yellow
