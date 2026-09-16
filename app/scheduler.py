"""
Agendador em Segundo Plano (APScheduler)
Executa verificações periódicas automáticas de preços e dispara notificações.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import get_settings
from app.scraper import check_all_products_now

import time

scheduler = AsyncIOScheduler()
_last_heartbeat = 0

async def scheduled_price_check():
    global _last_heartbeat
    now = time.time()
    try:
        res = await check_all_products_now()
        # Loga se disparou alerta ou como batimento cardíaco a cada 60s
        if res.get("triggered_alerts", 0) > 0:
            print(f"[Tempo Real 3s] 🔥 ALERTA DISPARADO: {res['triggered_alerts']} notificação(ões) enviada(s)!")
        elif now - _last_heartbeat >= 60.0:
            print(f"[Tempo Real 3s] Monitorando em tempo real... ({res['updated_products']} consoles ativos)")
            _last_heartbeat = now
    except Exception as e:
        print(f"[Scheduler] Erro durante verificação em tempo real: {e}")

def start_scheduler():
    settings = get_settings()
    interval_seconds = int(settings.get("check_interval_seconds", "3"))
    
    # Agendamento em tempo real (a cada 3 segundos por padrão)
    scheduler.add_job(
        scheduled_price_check,
        "interval",
        seconds=interval_seconds,
        id="periodic_ps5_price_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
    print(f"[Scheduler] Agendador em Tempo Real iniciado! Verificando a cada {interval_seconds} segundos.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("[Scheduler] Agendador finalizado.")
