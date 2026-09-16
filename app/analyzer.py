"""
Módulo de Análise Inteligente de Preços e Decisão de Compra
Calcula estatísticas de 3 anos, mínimas, máximas, médias móveis e veredito de compra.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from app.database import get_db

def get_product_summary(product_id: str) -> Dict[str, Any]:
    """
    Retorna métricas completas para um produto específico:
    - Preço atual e loja
    - Mínima histórica e data
    - Máxima histórica e data
    - Médias móveis (30d, 90d, 1y, total)
    - Score de Oportunidade (0 a 100)
    - Veredito de compra em linguagem natural
    """
    with get_db() as conn:
        # Informações do produto
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not prod:
            return {}
        
        # Último preço registrado
        latest = conn.execute("""
            SELECT * FROM daily_prices 
            WHERE product_id = ? 
            ORDER BY date DESC, id DESC LIMIT 1
        """, (product_id,)).fetchone()
        
        if not latest:
            return {"product": dict(prod), "has_data": False}
        
        current_price = latest["price"]
        current_store = latest["store"]
        current_date = latest["date"]
        current_url = latest["url"]
        
        # Menor preço de todos os tempos (Mínima Histórica)
        min_record = conn.execute("""
            SELECT * FROM daily_prices 
            WHERE product_id = ? 
            ORDER BY price ASC, date DESC LIMIT 1
        """, (product_id,)).fetchone()
        
        # Maior preço de todos os tempos (Máxima Histórica)
        max_record = conn.execute("""
            SELECT * FROM daily_prices 
            WHERE product_id = ? 
            ORDER BY price DESC, date DESC LIMIT 1
        """, (product_id,)).fetchone()
        
        # Médias móveis
        today_date = date.today()
        d30 = (today_date - timedelta(days=30)).strftime("%Y-%m-%d")
        d90 = (today_date - timedelta(days=90)).strftime("%Y-%m-%d")
        d365 = (today_date - timedelta(days=365)).strftime("%Y-%m-%d")
        
        avg_30d_val = conn.execute("""
            SELECT AVG(price) as avg_price FROM daily_prices 
            WHERE product_id = ? AND date >= ?
        """, (product_id, d30)).fetchone()["avg_price"] or current_price
        
        avg_90d_val = conn.execute("""
            SELECT AVG(price) as avg_price FROM daily_prices 
            WHERE product_id = ? AND date >= ?
        """, (product_id, d90)).fetchone()["avg_price"] or current_price
        
        avg_1y_val = conn.execute("""
            SELECT AVG(price) as avg_price FROM daily_prices 
            WHERE product_id = ? AND date >= ?
        """, (product_id, d365)).fetchone()["avg_price"] or current_price
        
        avg_all_val = conn.execute("""
            SELECT AVG(price) as avg_price FROM daily_prices 
            WHERE product_id = ?
        """, (product_id,)).fetchone()["avg_price"] or current_price

        min_price = min_record["price"]
        max_price = max_record["price"]
        
        # Diferenças percentuais
        diff_from_min_pct = round(((current_price - min_price) / min_price) * 100, 1)
        diff_from_avg90_pct = round(((current_price - avg_90d_val) / avg_90d_val) * 100, 1)
        discount_from_msrp_pct = round(((prod["msrp"] - current_price) / prod["msrp"]) * 100, 1)
        savings_vs_msrp = round(prod["msrp"] - current_price, 2)
        
        # Algoritmo de Score e Decisão de Compra
        # Score de 0 a 100
        if current_price <= min_price * 1.02:
            buy_score = 98
            verdict_code = "EXCELENTE"
            verdict_badge = "🔥 EXCELENTE MOMENTO PARA COMPRAR"
            verdict_color = "#10b981" # Verde esmeralda
            verdict_text = f"O preço atual de R$ {current_price:,.2f} está praticamente na MÍNIMA HISTÓRICA desde o lançamento oficial no Brasil (apenas {diff_from_min_pct}% acima do menor valor já registrado)! Grande chance de o estoque esgotar ou o preço subir logo."
        elif current_price <= min_price * 1.06:
            buy_score = 88
            verdict_code = "MUITO_BOM"
            verdict_badge = "🟢 ÓTIMO MOMENTO DE COMPRA"
            verdict_color = "#059669"
            verdict_text = f"Preço muito vantajoso! Está a apenas {diff_from_min_pct}% da mínima histórica e {abs(diff_from_avg90_pct)}% abaixo da média recente dos últimos 3 meses."
        elif current_price < avg_90d_val * 0.96:
            buy_score = 75
            verdict_code = "BOM"
            verdict_badge = "🟢 BOM MOMENTO"
            verdict_color = "#0284c7" # Azul PlayStation
            verdict_text = f"O valor atual está {abs(diff_from_avg90_pct)}% abaixo da média recente de 90 dias. É uma boa compra, especialmente se acompanhado de cupom ou cashback."
        elif current_price <= avg_90d_val * 1.03:
            buy_score = 55
            verdict_code = "REGULAR"
            verdict_badge = "🟡 PREÇO MÉDIO / ESTÁVEL"
            verdict_color = "#eab308" # Amarelo
            verdict_text = f"O preço está na média habitual de mercado. Se você tem pressa, não está pagando caro, mas se puder aguardar até a próxima data promocional, pode economizar cerca de R$ {abs(current_price - min_price):,.2f}."
        else:
            buy_score = 28
            verdict_code = "AGUARDE"
            verdict_badge = "🔴 AGUARDE UMA PROMOÇÃO"
            verdict_color = "#ef4444" # Vermelho
            verdict_text = f"Preço em alta! O console está {diff_from_avg90_pct}% acima da média recente e distante da mínima histórica. Não recomendamos comprar agora, a menos que seja estritamente necessário."
        
        # Histórico mensal (sazonalidade)
        monthly_avg = conn.execute("""
            SELECT strftime('%m', date) as month_num, AVG(price) as avg_p
            FROM daily_prices
            WHERE product_id = ?
            GROUP BY month_num
            ORDER BY avg_p ASC
        """, (product_id,)).fetchall()
        
        month_names = {
            "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
            "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
            "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
        }
        cheapest_months = [f"{month_names.get(r['month_num'], r['month_num'])} (méd. R$ {r['avg_p']:,.0f})" for r in monthly_avg[:3]]
        
        prod_dict = dict(prod)
        rdate = prod_dict.get("release_date")
        if rdate:
            try:
                parts = rdate.split("-")
                prod_dict["release_date_br"] = f"{parts[2]}/{parts[1]}/{parts[0]}"
            except Exception:
                prod_dict["release_date_br"] = rdate
                
        return {
            "product": prod_dict,
            "has_data": True,
            "current": {
                "price": current_price,
                "store": current_store,
                "date": current_date,
                "url": current_url,
                "discount_from_msrp_pct": discount_from_msrp_pct,
                "savings_vs_msrp": savings_vs_msrp
            },
            "history_extremes": {
                "min_price": min_price,
                "min_date": min_record["date"],
                "min_store": min_record["store"],
                "max_price": max_price,
                "max_date": max_record["date"],
                "max_store": max_record["store"]
            },
            "averages": {
                "avg_30d": round(avg_30d_val, 2),
                "avg_90d": round(avg_90d_val, 2),
                "avg_1y": round(avg_1y_val, 2),
                "avg_all": round(avg_all_val, 2)
            },
            "differences": {
                "diff_from_min_pct": diff_from_min_pct,
                "diff_from_avg90_pct": diff_from_avg90_pct
            },
            "recommendation": {
                "score": buy_score,
                "code": verdict_code,
                "badge": verdict_badge,
                "color": verdict_color,
                "explanation": verdict_text,
                "best_months_hint": ", ".join(cheapest_months)
            }
        }

def get_price_history_series(product_id: str, range_key: str = "launch") -> Dict[str, Any]:
    """
    Retorna a série temporal formatada para renderização direta no Chart.js.
    range_key: '30d', '90d', '1y', '3y', 'launch', 'all'
    """
    today_date = date.today()
    days_map = {
        "30d": 30,
        "90d": 90,
        "1y": 365,
        "3y": 1095,
        "launch": 3000,
        "all": 3000
    }
    
    with get_db() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        release_date = prod["release_date"] if prod and "release_date" in prod.keys() and prod["release_date"] else None
        
        # Se range for 'launch', 'all' ou '3y', assegura que inicia a partir da data de lançamento oficial no Brasil
        if range_key in ("launch", "all", "3y"):
            start_date_str = release_date or (today_date - timedelta(days=1095)).strftime("%Y-%m-%d")
        else:
            days = days_map.get(range_key, 1095)
            start_date_str = (today_date - timedelta(days=days)).strftime("%Y-%m-%d")
            if release_date and start_date_str < release_date:
                start_date_str = release_date

        rows = conn.execute("""
            SELECT date, price, store, is_promo 
            FROM daily_prices 
            WHERE product_id = ? AND date >= ?
            ORDER BY date ASC
        """, (product_id, start_date_str)).fetchall()
        
        # Obter a média do período e a mínima para traçar linhas de referência
        if rows:
            prices = [r["price"] for r in rows]
            avg_period = round(sum(prices) / len(prices), 2)
            min_period = min(prices)
            max_period = max(prices)
        else:
            avg_period = 0
            min_period = 0
            max_period = 0
            
        labels = [r["date"] for r in rows]
        data_prices = [r["price"] for r in rows]
        stores = [r["store"] for r in rows]
        promos = [bool(r["is_promo"]) for r in rows]
        
        # Formatação brasileira da data de lançamento
        release_date_br = None
        if release_date:
            try:
                parts = release_date.split("-")
                release_date_br = f"{parts[2]}/{parts[1]}/{parts[0]}"
            except Exception:
                release_date_br = release_date
        
        return {
            "product_id": product_id,
            "range": range_key,
            "release_date": release_date,
            "release_date_br": release_date_br,
            "start_date": labels[0] if labels else start_date_str,
            "total_points": len(rows),
            "stats": {
                "avg": avg_period,
                "min": min_period,
                "max": max_period
            },
            "labels": labels,
            "prices": data_prices,
            "stores": stores,
            "is_promo": promos
        }

def get_store_comparisons(product_id: str) -> List[Dict[str, Any]]:
    """
    Retorna o comparativo de preços entre todas as lojas monitoradas trazendo a cotação mais recente de cada uma.
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.store, p.price, p.original_price, p.url, p.in_stock, p.date, p.created_at
            FROM daily_prices p
            INNER JOIN (
                SELECT store, MAX(id) as max_id
                FROM daily_prices
                WHERE product_id = ?
                GROUP BY store
            ) latest ON p.id = latest.max_id
            WHERE p.product_id = ?
            ORDER BY p.price ASC
        """, (product_id, product_id)).fetchall()
        
        today_str = date.today().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        results = []
        for r in rows:
            d = dict(r)
            d["is_today"] = (d["date"] == today_str)
            if d.get("created_at") and " " in d["created_at"]:
                d["time"] = d["created_at"].split()[1][:8]
            else:
                d["time"] = now_time
            results.append(d)
        return results
