"""
Ponto de Entrada Principal - Monitor de Preços PS5 e PS5 Pro
Inicia o servidor web local e abre o navegador automaticamente.
"""
import sys
import os
import time
import threading
import webbrowser
import uvicorn

# Garantir encoding UTF-8 no Windows
sys.stdout.reconfigure(encoding='utf-8')

def open_browser():
    """Aguarda 1.5 segundo e abre o painel no navegador padrão."""
    time.sleep(1.5)
    url = "http://localhost:8000"
    print(f"\n[Monitor PS5] Abrindo interface no navegador: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[Monitor PS5] Não foi possível abrir o navegador automaticamente: {e}")

def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    is_production = os.environ.get("RENDER") is not None or os.environ.get("RAILWAY_ENVIRONMENT") is not None

    print("=" * 65)
    print("   🎮 MONITOR DE PREÇOS PLAYSTATION 5 & PS5 PRO")
    print("   Histórico Diário • Decisão Inteligente • Notificações")
    print("=" * 65)
    print(f"\n[Status] Inicializando servidor web em http://{host}:{port} ...")

    # Thread para abrir o navegador se estiver rodando localmente
    if not is_production and host in ("0.0.0.0", "127.0.0.1", "localhost"):
        threading.Thread(target=open_browser, daemon=True).start()

    # Executar FastAPI via Uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=not is_production,
        log_level="info"
    )

if __name__ == "__main__":
    main()
