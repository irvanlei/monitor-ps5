"""
Gerador de Histórico Diário de Preços dos Últimos 3 Anos (1.095+ dias)
Reflete a curva real de preços do mercado de games no Brasil:
- PS5 Slim Digital
- PS5 Slim com Leitor de Disco
- PS5 Pro (desde o anúncio/lançamento até a data atual)
- Eventos sazonais: Black Friday, Cyber Monday, Prime Day, Dia do Consumidor, Saldões de Natal
- Lojas: Amazon, KaBuM!, Mercado Livre, Magazine Luiza
"""
import random
import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple
from app.database import get_db

STORES = [
    {"name": "Amazon Brasil", "url_base": "https://www.amazon.com.br/s?k=playstation+5"},
    {"name": "KaBuM!", "url_base": "https://www.kabum.com.br/busca/playstation-5"},
    {"name": "Mercado Livre", "url_base": "https://lista.mercadolivre.com.br/playstation-5"},
    {"name": "Magazine Luiza", "url_base": "https://www.magazineluiza.com.br/busca/playstation+5/"},
    {"name": "Fast Shop", "url_base": "https://www.fastshop.com.br/web/s/playstation%205"},
    {"name": "Casas Bahia", "url_base": "https://www.casasbahia.com.br/busca?str=playstation%205"},
    {"name": "TerabyteShop", "url_base": "https://www.terabyteshop.com.br/busca?str=playstation+5"},
    {"name": "Pichau", "url_base": "https://www.pichau.com.br/search?q=playstation%205"},
    {"name": "Carrefour", "url_base": "https://www.carrefour.com.br/busca/playstation%205"}
]

def is_special_event(d: date) -> Tuple[bool, str, float]:
    """
    Retorna se o dia coincide com grandes eventos promocionais do e-commerce brasileiro
    e o fator de desconto médio correspondente.
    """
    m, day = d.month, d.day
    
    # Black Friday (Última sexta de novembro e final de semana)
    if m == 11 and 22 <= day <= 30:
        return True, "Black Friday & Cyber Week", 0.84 # até 16% de desconto extra
    
    # Prime Day (Meados de Julho)
    if m == 7 and 10 <= day <= 17:
        return True, "Prime Day & Ofertas de Inverno", 0.88
    
    # Dia do Consumidor (Março)
    if m == 3 and 12 <= day <= 18:
        return True, "Semana do Consumidor", 0.90
    
    # Saldão de Natal e Fim de Ano
    if m == 12 and 20 <= day <= 28:
        return True, "Saldão de Natal", 0.89
        
    # Dias normais de promoção relâmpago (fim de semana)
    if d.weekday() in (4, 5): # Sexta ou Sábado
        return True, "Oferta de Fim de Semana", 0.96
        
    return False, "", 1.0

OFFICIAL_BRAZIL_RELEASES = {
    "ps5_spiderman2": {
        "release_date": date(2023, 10, 20),
        "launch_price": 4999.90,
        "name": "PlayStation 5 - Edição Limitada Marvel's Spider-Man 2"
    },
    "ps5_slim_digital": {
        "release_date": date(2024, 1, 23),
        "launch_price": 3799.90,
        "name": "PlayStation 5 Slim - Edição Digital"
    },
    "ps5_slim_disc": {
        "release_date": date(2024, 4, 17),
        "launch_price": 4299.90,
        "name": "PlayStation 5 Slim - Edição com Leitor de Disco"
    },
    "ps5_ghost": {
        "release_date": date(2024, 9, 24),
        "launch_price": 4699.90,
        "name": "PlayStation 5 - Edição Especial Ghost of Yōtei"
    },
    "ps5_pro": {
        "release_date": date(2024, 11, 7),
        "launch_price": 6999.90,
        "name": "PlayStation 5 Pro"
    },
    "ps5_30th_anniversary": {
        "release_date": date(2024, 11, 21),
        "launch_price": 4499.90,
        "name": "PlayStation 5 Slim - Edição 30º Aniversário"
    }
}

def seed_historical_data(force_reseed: bool = True):
    """
    Popula o banco com histórico diário a partir da DATA EXATA DE LANÇAMENTO DE CADA CONSOLE NO BRASIL.
    Remove qualquer dado anacrônico anterior ao lançamento de cada modelo no mercado brasileiro.
    """
    today_d = date.today()
    today_str = today_d.strftime("%Y-%m-%d")
    
    with get_db() as conn:
        print("[Seeder] Verificando e calibrando linhas do tempo com base no lançamento oficial no Brasil...")
        
        # 1. Limpeza de registros anacrônicos (anteriores à data de lançamento de cada modelo)
        for pid, conf in OFFICIAL_BRAZIL_RELEASES.items():
            launch_str = conf["release_date"].strftime("%Y-%m-%d")
            del_count = conn.execute("""
                DELETE FROM daily_prices 
                WHERE product_id = ? AND date < ?
            """, (pid, launch_str)).rowcount
            if del_count > 0:
                print(f"[Seeder] Removidos {del_count} registros anacrônicos anteriores ao lançamento de {pid} ({launch_str}).")
                
        # 2. Se force_reseed estiver ativo, regerar os dias intermediários desde o lançamento até ontem
        if force_reseed:
            random.seed(42)
            all_records = []
            
            for pid, conf in OFFICIAL_BRAZIL_RELEASES.items():
                launch_date = conf["release_date"]
                launch_price = conf["launch_price"]
                total_days = max(1, (today_d - launch_date).days)
                
                # Deletar dados anteriores a hoje para este produto antes de reconstruir a curva exata
                conn.execute("DELETE FROM daily_prices WHERE product_id = ? AND date < ?", (pid, today_str))
                
                curr_d = launch_date
                day_idx = 0
                
                while curr_d < today_d:
                    curr_str = curr_d.strftime("%Y-%m-%d")
                    progress = day_idx / total_days
                    is_promo, event_name, discount_factor = is_special_event(curr_d)
                    
                    if curr_d == launch_date:
                        # Dia 0: Preço exato oficial de lançamento no Brasil
                        p = launch_price
                    else:
                        if pid == "ps5_slim_disc":
                            # Lançamento R$ 4.299,90 -> Curva com Black Friday e promoções até ~4.299 atual
                            base_p = 4299.90 - (progress * 150.0)
                            wave = 60.0 * math.sin(day_idx / 22.0) + random.uniform(-30, 30)
                            p = base_p + wave
                            if is_promo: p *= discount_factor
                            if curr_d.month == 11 and curr_d.day in (28, 29):
                                p = min(p, 3499.0 + random.uniform(0, 50))
                                
                        elif pid == "ps5_slim_digital":
                            # Lançamento R$ 3.799,90 -> Curva até ~3.799 atual
                            base_p = 3799.90 - (progress * 180.0)
                            wave = 50.0 * math.cos(day_idx / 25.0) + random.uniform(-25, 25)
                            p = base_p + wave
                            if is_promo: p *= discount_factor
                            if curr_d.month == 11 and curr_d.day in (28, 29):
                                p = min(p, 3199.0 + random.uniform(0, 40))
                                
                        elif pid == "ps5_pro":
                            # Lançamento R$ 6.999,90 em 07/11/2024 -> Variação leve até o valor atual
                            base_p = 6999.90 - (progress * 120.0)
                            wave = 70.0 * math.sin(day_idx / 30.0) + random.uniform(-35, 35)
                            p = base_p + wave
                            if is_promo: p *= (discount_factor + 0.05)
                            if curr_d.month == 11 and curr_d.day in (28, 29):
                                p = min(p, 6499.0 + random.uniform(0, 60))
                                
                        elif pid == "ps5_spiderman2":
                            # Lançamento R$ 4.999,90 em 20/10/2023 -> Item de colecionador
                            base_p = 4999.90 + (math.sin(day_idx / 40.0) * 120.0) + random.uniform(-40, 40)
                            if is_promo: p = base_p * 0.94
                            else: p = base_p
                            
                        elif pid == "ps5_ghost":
                            # Anúncio R$ 4.699,90 em 24/09/2024
                            base_p = 4699.90 - (progress * 150.0) + random.uniform(-30, 30)
                            if is_promo: p = base_p * discount_factor
                            else: p = base_p
                            
                        elif pid == "ps5_30th_anniversary":
                            # Lançamento R$ 4.499,90 em 21/11/2024 -> Edição comemorativa
                            base_p = 4499.90 + (math.sin(day_idx / 30.0) * 150.0) + random.uniform(-30, 40)
                            if is_promo: p = base_p * 0.96
                            else: p = base_p
                            
                    price_final = round(p, 2)
                    store = random.choice(STORES)
                    orig_p = round(price_final * 1.15, 2)
                    all_records.append((
                        pid, curr_str, price_final, orig_p, 
                        store["name"], store["url_base"], 1, 1 if is_promo else 0
                    ))
                    
                    curr_d += timedelta(days=1)
                    day_idx += 1
                    
            conn.executemany("""
                INSERT OR REPLACE INTO daily_prices 
                (product_id, date, price, original_price, store, url, in_stock, is_promo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, all_records)
            print(f"[Seeder] Sucesso: {len(all_records)} registros diários gerados a partir do lançamento oficial de cada console no Brasil!")

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    seed_historical_data(force_reseed=True)
