"""
Serviço de Notificações Multi-Canal:
- Discord Webhook (com Embeds ricos e botões de compra)
- Telegram Bot API
- Email (SMTP via HTML)
- Registro de logs e notificações no navegador
"""
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.database import get_db, get_settings, log_notification, get_product

async def send_discord_notification(webhook_url: str, title: str, description: str, 
                                  product_name: str, price: float, store: str, 
                                  url: str, image_url: Optional[str] = None, 
                                  verdict_badge: str = "", is_all_time_low: bool = False) -> Dict[str, Any]:
    if not webhook_url or not webhook_url.strip():
        return {"success": False, "error": "URL do Webhook do Discord não configurada."}
    
    # Cor: Dourado/Verde para mínima histórica, Azul PlayStation para alertas comuns
    color_code = 0x10b981 if is_all_time_low else 0x0070d1
    
    embed = {
        "title": f"🚨 {title}",
        "description": description,
        "color": color_code,
        "fields": [
            {"name": "🎮 Console", "value": product_name, "inline": False},
            {"name": "💰 Preço Atual", "value": f"**R$ {price:,.2f}**", "inline": True},
            {"name": "🏬 Loja", "value": store, "inline": True},
            {"name": "📊 Status / Veredito", "value": verdict_badge or "Alerta de Preço Disparado", "inline": False}
        ],
        "footer": {
            "text": "PS5 Price Tracker Local • Monitoramento 3 Anos",
            "icon_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/PlayStation_logo.svg/200px-PlayStation_logo.svg.png"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if image_url:
        embed["thumbnail"] = {"url": image_url}
        
    if url:
        embed["fields"].append({"name": "🔗 Link da Oferta", "value": f"[Clique aqui para comprar no site da {store}]({url})", "inline": False})
        
    payload = {
        "username": "PS5 Price Monitor",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/PlayStation_logo.svg/200px-PlayStation_logo.svg.png",
        "embeds": [embed]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code in (200, 204):
                return {"success": True}
            else:
                return {"success": False, "error": f"Discord retornou status {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "error": f"Erro de conexão com Discord: {str(e)}"}

async def send_telegram_notification(bot_token: str, chat_id: str, title: str,
                                    product_name: str, price: float, store: str,
                                    url: str, verdict_badge: str = "") -> Dict[str, Any]:
    if not bot_token or not chat_id:
        return {"success": False, "error": "Token do Bot ou Chat ID do Telegram não configurados."}
        
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    msg_lines = [
        f"🚨 *{title}*",
        "",
        f"🎮 *Console:* {product_name}",
        f"💰 *Preço:* R$ {price:,.2f}",
        f"🏬 *Loja:* {store}",
        f"📊 *Recomendação:* {verdict_badge}",
        "",
        f"🛒 [Ver Oferta na {store}]({url})" if url else "",
        "",
        "_Monitor de Preços PS5 - Execução Local_"
    ]
    text = "\n".join([line for line in msg_lines if line])
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, json=payload)
            data = resp.json()
            if data.get("ok"):
                return {"success": True}
            else:
                return {"success": False, "error": data.get("description", "Erro desconhecido da API do Telegram")}
    except Exception as e:
        return {"success": False, "error": f"Erro de conexão com Telegram: {str(e)}"}

def send_email_notification(smtp_host: str, smtp_port: int, user: str, password: str,
                           recipient: str, title: str, product_name: str,
                           price: float, store: str, url: str) -> Dict[str, Any]:
    if not smtp_host or not user or not password or not recipient:
        return {"success": False, "error": "Configurações de SMTP incompletas."}
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[PS5 Monitor] {title} - R$ {price:,.2f}"
    msg["From"] = user
    msg["To"] = recipient
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #1e293b; border-radius: 12px; padding: 25px; border: 1px solid #334155;">
            <h2 style="color: #38bdf8; margin-top: 0;">🎮 {title}</h2>
            <p style="font-size: 16px;">O preço monitorado atingiu a sua meta configurada!</p>
            <div style="background: #0f172a; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Console:</strong> {product_name}</p>
                <p style="margin: 5px 0;"><strong>Preço Atual:</strong> <span style="color: #4ade80; font-size: 20px; font-weight: bold;">R$ {price:,.2f}</span></p>
                <p style="margin: 5px 0;"><strong>Loja:</strong> {store}</p>
            </div>
            <a href="{url}" style="display: inline-block; background: #0070d1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Acessar Oferta</a>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 25px;">Notificação gerada pelo PS5 Monitor Local.</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Erro ao enviar email: {str(e)}"}

async def test_channel_notification(channel: str) -> Dict[str, Any]:
    """
    Dispara uma mensagem de teste para o canal especificado (discord, telegram, email).
    """
    settings = get_settings()
    
    test_title = "Teste de Notificação - Monitor PS5"
    test_desc = "Esta é uma notificação de verificação disparada pelo seu painel local do Monitor de Preços do PS5!"
    test_prod = "PlayStation 5 Slim com Leitor de Disco"
    test_price = 3699.90
    test_store = "Amazon Brasil"
    test_url = "https://www.amazon.com.br"
    test_img = "https://m.media-amazon.com/images/I/610x2984k+L._AC_SX679_.jpg"
    
    if channel == "discord":
        url = settings.get("discord_webhook_url", "").strip()
        res = await send_discord_notification(url, test_title, test_desc, test_prod, test_price, test_store, test_url, test_img, "🟡 TESTE DE CONECTIVIDADE", False)
        status = "sent" if res["success"] else "failed"
        log_notification("ps5_slim_disc", test_price, "discord", status, "Disparo de teste manual: " + (res.get("error") or "Sucesso"))
        return res
        
    elif channel == "telegram":
        token = settings.get("telegram_bot_token", "").strip()
        chat_id = settings.get("telegram_chat_id", "").strip()
        res = await send_telegram_notification(token, chat_id, test_title, test_prod, test_price, test_store, test_url, "🟡 TESTE DE CONECTIVIDADE")
        status = "sent" if res["success"] else "failed"
        log_notification("ps5_slim_disc", test_price, "telegram", status, "Disparo de teste manual: " + (res.get("error") or "Sucesso"))
        return res
        
    elif channel == "email":
        host = settings.get("email_smtp_host", "").strip()
        port = int(settings.get("email_smtp_port", "587"))
        user = settings.get("email_user", "").strip()
        pwd = settings.get("email_password", "").strip()
        recip = settings.get("email_recipient", "").strip()
        res = send_email_notification(host, port, user, pwd, recip, test_title, test_prod, test_price, test_store, test_url)
        status = "sent" if res["success"] else "failed"
        log_notification("ps5_slim_disc", test_price, "email", status, "Disparo de teste manual: " + (res.get("error") or "Sucesso"))
        return res
        
    return {"success": False, "error": f"Canal '{channel}' desconhecido."}

async def trigger_alerts_if_needed(product_id: str, price: float, store: str, url: str) -> List[Dict[str, Any]]:
    """
    Verifica se o preço atual ativa algum alerta cadastrado no banco de dados e realiza os disparos.
    """
    with get_db() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not prod:
            return []
            
        alerts = conn.execute("""
            SELECT * FROM alerts 
            WHERE product_id = ? AND is_active = 1
        """, (product_id,)).fetchall()
        
        # Obter menor preço histórico dos últimos 3 anos
        min_record = conn.execute("""
            SELECT MIN(price) as min_p FROM daily_prices WHERE product_id = ?
        """, (product_id,)).fetchone()
        all_time_min = min_record["min_p"] if min_record and min_record["min_p"] else price
        
        is_all_time_low = price <= all_time_min
        triggered_results = []
        settings = get_settings()
        
        for alert in alerts:
            should_fire = False
            reason = ""
            
            # Condição 1: Preço abaixo do alvo configurado
            if price <= alert["target_price"]:
                should_fire = True
                reason = f"Preço (R$ {price:,.2f}) atingiu a meta de R$ {alert['target_price']:,.2f}!"
            # Condição 2: Bateu nova mínima histórica e o alerta permite
            elif is_all_time_low and alert["alert_on_all_time_low"]:
                should_fire = True
                reason = f"🔥 NOVA MÍNIMA HISTÓRICA: R$ {price:,.2f} na {store}!"
                
            if should_fire:
                title = "🚨 OFERTA DETECTADA: " + prod["name"]
                desc = f"Identificamos uma oportunidade de compra na **{store}**!\n{reason}"
                channel = alert["channel"]
                
                # Discord
                if channel in ("all", "discord") and settings.get("notify_discord") == "1":
                    d_url = settings.get("discord_webhook_url")
                    if d_url:
                        res = await send_discord_notification(d_url, title, desc, prod["name"], price, store, url, prod["image_url"], "🔥 COMPRA RECOMENDADA", is_all_time_low)
                        log_notification(product_id, price, "discord", "sent" if res["success"] else "failed", reason)
                        triggered_results.append({"channel": "discord", "result": res})
                
                # Telegram
                if channel in ("all", "telegram") and settings.get("notify_telegram") == "1":
                    t_token = settings.get("telegram_bot_token")
                    t_chat = settings.get("telegram_chat_id")
                    if t_token and t_chat:
                        res = await send_telegram_notification(t_token, t_chat, title, prod["name"], price, store, url, "🔥 COMPRA RECOMENDADA")
                        log_notification(product_id, price, "telegram", "sent" if res["success"] else "failed", reason)
                        triggered_results.append({"channel": "telegram", "result": res})
                        
                # Email
                if channel in ("all", "email"):
                    host = settings.get("email_smtp_host")
                    port = int(settings.get("email_smtp_port", "587"))
                    user = settings.get("email_user")
                    pwd = settings.get("email_password")
                    recip = settings.get("email_recipient")
                    if host and user and pwd and recip:
                        res = send_email_notification(host, port, user, pwd, recip, title, prod["name"], price, store, url)
                        log_notification(product_id, price, "email", "sent" if res["success"] else "failed", reason)
                        triggered_results.append({"channel": "email", "result": res})
                        
                # Atualizar data de último disparo do alerta
                conn.execute("UPDATE alerts SET last_triggered_at = CURRENT_TIMESTAMP WHERE id = ?", (alert["id"],))
                
        return triggered_results
