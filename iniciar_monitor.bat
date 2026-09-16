@echo off
title Monitor de Precos PS5 e PS5 Pro - Local
chcp 65001 > nul
cd /d "%~dp0"

echo ======================================================================
echo    🎮 MONITOR DE PREÇOS PLAYSTATION 5 & PS5 PRO
echo    Histórico Diário de 3 Anos • Recomendação de Compra • Alertas
echo ======================================================================
echo.

:: Verifica se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo [Setup] Criando ambiente virtual Python...
    python -m venv venv
    if errorlevel 1 (
        echo [Erro] Falha ao criar o ambiente virtual. Verifique se o Python está instalado no PATH.
        pause
        exit /b 1
    )
    echo [Setup] Instalando dependências (FastAPI, Uvicorn, Chart.js, etc)...
    venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [Erro] Falha ao instalar as dependências.
        pause
        exit /b 1
    )
)

echo [Iniciando] Servidor web iniciando em http://localhost:8000 ...
echo [Info] Seu navegador padrão abrirá automaticamente.
echo [Dica] Pressione CTRL + C nesta janela quando quiser fechar o monitor.
echo.

venv\Scripts\python.exe run.py

if errorlevel 1 (
    echo.
    echo Ocorreu um erro na execução do servidor.
    pause
)
