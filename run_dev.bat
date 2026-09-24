@echo off
title Calculadora de Impressao 3D - Servidor de Desenvolvimento
echo =======================================================
echo   Iniciando Calculadora de Impressao 3D (Supabase VPS)
echo =======================================================
echo.

set APP_ENV=development
set DATABASE_URL=postgresql+psycopg://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres
set DB_SCHEMA=3dprintcalc

python -c "import psycopg" 2>NUL
if errorlevel 1 (
    echo [AVISO] Dependencias nao encontradas. Instalando requirements.txt...
    pip install -r requirements.txt
)

echo Iniciando servidor FastAPI em http://localhost:8000 ...
python app.py

pause
