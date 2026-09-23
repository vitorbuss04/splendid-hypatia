@echo off
title Calculadora de Impressao 3D - Servidor de Desenvolvimento
echo =======================================================
echo   Iniciando Calculadora de Impressao 3D (Dev Mode)
echo =======================================================
echo.

set APP_ENV=development
set DATABASE_URL=sqlite:///data/dev.db

python -c "import fastapi" 2>NUL
if errorlevel 1 (
    echo [AVISO] Dependencias nao encontradas. Instalando requirements.txt...
    pip install -r requirements.txt
)

echo Iniciando servidor FastAPI em http://localhost:8000 ...
python app.py

pause
