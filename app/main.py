"""
Aplicação Principal FastAPI - Monitor de Preços PS5 e PS5 Pro
"""
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.database import (
    init_db, get_products, get_product, get_settings, 
    update_setting, get_alerts, add_alert, delete_alert, 
    get_notification_logs
)
from app.seeder import seed_historical_data
from app.analyzer import get_product_summary, get_price_history_series, get_store_comparisons
from app.scraper import check_all_products_now, simulate_flash_sale
from app.notifier import test_channel_notification
from app.scheduler import start_scheduler, stop_scheduler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização
    print("[FastAPI] Inicializando banco de dados...")
    init_db()
    # Verifica e gera histórico de 3 anos caso necessário
    seed_historical_data()
    print("[FastAPI] Coletando preços reais ao vivo do mercado brasileiro...")
    try:
        await check_all_products_now(force_baseline=True)
    except Exception as e:
        print(f"[FastAPI] Aviso ao coletar base inicial: {e}")
    # Inicia agendador
    try:
        start_scheduler()
    except Exception as e:
        print(f"[FastAPI] Aviso ao iniciar agendador: {e}")
    yield
    # Encerramento
    stop_scheduler()

app = FastAPI(
    title="Monitor de Preços PS5 & PS5 Pro",
    description="Aplicação local para rastreamento de preços, histórico de 3 anos e alertas de compra.",
    version="1.0.0",
    lifespan=lifespan
)

# Servir arquivos estáticos e templates
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Schemas Pydantic
class AlertCreate(BaseModel):
    product_id: str
    target_price: float
    alert_on_all_time_low: bool = True
    channel: str = "all"

class SettingsUpdate(BaseModel):
    discord_webhook_url: Optional[str] = ""
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    email_smtp_host: Optional[str] = "smtp.gmail.com"
    email_smtp_port: Optional[str] = "587"
    email_user: Optional[str] = ""
    email_password: Optional[str] = ""
    email_recipient: Optional[str] = ""
    check_interval_hours: Optional[str] = "6"
    notify_discord: Optional[str] = "1"
    notify_telegram: Optional[str] = "1"

class TestNotificationRequest(BaseModel):
    channel: str # "discord", "telegram", "email"

class SimulateSaleRequest(BaseModel):
    product_id: str
    promo_price: float
    store: Optional[str] = "KaBuM!"

# Rotas de Interface
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    products = get_products()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"products": products}
    )

# Rotas de API REST
@app.get("/api/products")
async def api_get_products():
    """Retorna a lista de produtos com resumo atual de preços e recomendação de compra."""
    products = get_products()
    summaries = []
    for p in products:
        summary = get_product_summary(p["id"])
        summaries.append(summary)
    return summaries

@app.get("/api/product/{product_id}")
async def api_get_product(product_id: str):
    """Retorna detalhes e análises de compra de um produto específico."""
    summary = get_product_summary(product_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return summary

@app.get("/api/history/{product_id}")
async def api_get_history(product_id: str, range: str = Query("launch", pattern="^(30d|90d|1y|3y|launch|all)$")):
    """Retorna a série temporal dia a dia a partir da data de lançamento no Brasil."""
    return get_price_history_series(product_id, range)

@app.get("/api/stores/{product_id}")
async def api_get_stores(product_id: str):
    """Retorna a cotação por loja para o console selecionado."""
    return get_store_comparisons(product_id)

@app.post("/api/check-now")
async def api_check_now():
    """Força uma verificação imediata dos preços em todas as lojas."""
    return await check_all_products_now()

@app.post("/api/simulate-sale")
async def api_simulate_sale(req: SimulateSaleRequest):
    """Simula uma oferta relâmpago para testar gatilhos e notificações."""
    return await simulate_flash_sale(req.product_id, req.promo_price, req.store)

@app.get("/api/alerts")
async def api_get_alerts():
    """Lista todos os alertas de preço cadastrados."""
    return get_alerts()

@app.post("/api/alerts")
async def api_create_alert(alert: AlertCreate):
    """Cadastra uma nova meta de preço."""
    alert_id = add_alert(
        alert.product_id,
        alert.target_price,
        alert.alert_on_all_time_low,
        alert.channel
    )
    return {"status": "created", "id": alert_id}

@app.delete("/api/alerts/{alert_id}")
async def api_delete_alert(alert_id: int):
    """Exclui um alerta de preço."""
    delete_alert(alert_id)
    return {"status": "deleted"}

@app.get("/api/settings")
async def api_get_settings():
    """Retorna as configurações atuais de notificação."""
    return get_settings()

@app.post("/api/settings")
async def api_update_settings(settings: SettingsUpdate):
    """Atualiza configurações de Webhook, Telegram e Email."""
    for key, value in settings.model_dump().items():
        if value is not None:
            update_setting(key, str(value))
    return {"status": "saved"}

@app.post("/api/test-notification")
async def api_test_notification(req: TestNotificationRequest):
    """Dispara um teste no canal especificado."""
    result = await test_channel_notification(req.channel)
    return result

@app.get("/api/logs")
async def api_get_logs(limit: int = 25):
    """Retorna o histórico de notificações disparadas."""
    return get_notification_logs(limit)
