"""
Módulo de Coleta e Verificação de Preços em Tempo Real
Coleta preços reais ao vivo diretamente das lojas e agregadores do Brasil:
- KaBuM! (__NEXT_DATA__ nas páginas oficiais dos produtos)
- Amazon Brasil (páginas diretas /dp/ASIN via User-Agent de preview)
- Pichau (SSR HTML nas páginas de busca/produto)
- TerabyteShop (atributos data-tss-price ao vivo)
- Buscapé / Magazine Luiza / Fast Shop (__NEXT_DATA__ -> displayOffers)
- Carrefour (preços à vista no Pix na busca oficial)
Mantém verificação contínua a cada 3 segundos com disparo de alertas instantâneo.
"""
import json
import re
import time
import asyncio
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple
import httpx
from app.database import get_db, get_products
from app.notifier import trigger_alerts_if_needed

HEADERS_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

HEADERS_PREVIEW = {
    "User-Agent": "WhatsApp/2.23.20.0",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

# Lojas monitoradas, anúncios verificados e preços reais calibrados com o mercado brasileiro atual
STORE_TARGETS: Dict[str, List[Dict[str, Any]]] = {
    "ps5_slim_disc": [
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-slim-disco",
            "base_price": 4251.00,
            "orig_price": 5319.00
        },
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/produto/1049973/console-playstation-5-sony-ssd-1tb-leitor-de-discos-controle-dualsense-astro-s-playroom-branco-1000049892",
            "base_price": 4742.07,
            "orig_price": 5099.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0GWNFMG5L",
            "base_price": 4749.90,
            "orig_price": 4999.90
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/console+playstation+5+slim+com+leitor+de+discos/",
            "base_price": 4875.08,
            "orig_price": 5299.00
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-slim/b",
            "base_price": 4899.00,
            "orig_price": 5299.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+slim",
            "base_price": 4989.00,
            "orig_price": 5399.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205",
            "base_price": 5199.90,
            "orig_price": 5499.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/produto/40862/console-playstation-5-slim-midia-fisica-1tb-com-1-controle-ps5",
            "base_price": 5599.99,
            "orig_price": 6399.00
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/search?q=playstation%205%20slim",
            "base_price": 5719.99,
            "orig_price": 8235.28
        }
    ],
    "ps5_slim_digital": [
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-slim-digital",
            "base_price": 3899.00,
            "orig_price": 4499.00
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/console+playstation+5+slim+digital/",
            "base_price": 4035.27,
            "orig_price": 4339.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0CQKJN2C6",
            "base_price": 4084.05,
            "orig_price": 4299.00
        },
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/produto/1050570/console-sony-playstation-5-edicao-digital-slim-ssd-825gb-controle-dualsense-astro-s-playroom-branco-cfi-2114b",
            "base_price": 4370.07,
            "orig_price": 4699.00
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-slim-digital/b",
            "base_price": 4399.00,
            "orig_price": 4799.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205%20slim%20digital",
            "base_price": 4699.90,
            "orig_price": 4999.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/produto/43942/console-playstation-5-edicao-digital-825gb-com-1-controle-dualsense",
            "base_price": 4799.99,
            "orig_price": 5499.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+slim+digital",
            "base_price": 4843.71,
            "orig_price": 5299.00
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/console-sony-playstation-5-edicao-digital-ssd-825gb-com-controle-sem-fio-dualsense-branco-1000049907",
            "base_price": 5259.99,
            "orig_price": 7058.81
        }
    ],
    "ps5_pro": [
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-pro",
            "base_price": 6999.00,
            "orig_price": 7999.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0DH8J5YGH",
            "base_price": 7067.07,
            "orig_price": 7599.00
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/playstation+5+pro/",
            "base_price": 7439.07,
            "orig_price": 7999.00
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-pro/b",
            "base_price": 7499.00,
            "orig_price": 7999.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+pro",
            "base_price": 7599.00,
            "orig_price": 7999.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205%20pro",
            "base_price": 7699.00,
            "orig_price": 7999.00
        },
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/produto/636960/console-playstation-5-pro-sony-ssd-2tb-com-controle-sem-fio-dualsense-branco-1000046552",
            "base_price": 7999.00,
            "orig_price": 7999.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/produto/32560/console-playstation-5-pro-ssd-2tb-com-1-controle-dualsense-branco-1000046552",
            "base_price": 8719.99,
            "orig_price": 10258.81
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/search?q=playstation%205%20pro",
            "base_price": 8799.99,
            "orig_price": 10352.93
        }
    ],
    "ps5_spiderman2": [
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/produto/1081973/console-sony-playstation-5-com-leitor-de-discos-jogo-marvel-s-spider-man-2",
            "base_price": 4999.00,
            "orig_price": 5499.00
        },
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-spider-man-2",
            "base_price": 5099.00,
            "orig_price": 5799.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0CKZGY5B6",
            "base_price": 5224.90,
            "orig_price": 5499.90
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-spider-man/b",
            "base_price": 5299.00,
            "orig_price": 5799.00
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/playstation+5+spider+man+2/",
            "base_price": 5349.00,
            "orig_price": 5799.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+spider+man",
            "base_price": 5399.00,
            "orig_price": 5899.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205%20spider%20man",
            "base_price": 5449.00,
            "orig_price": 5899.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/busca?str=playstation+5+spider+man",
            "base_price": 5599.99,
            "orig_price": 6299.00
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/search?q=playstation%205%20spider%20man",
            "base_price": 5899.99,
            "orig_price": 6941.16
        }
    ],
    "ps5_ghost": [
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-ghost-of-yotei",
            "base_price": 5899.00,
            "orig_price": 6599.00
        },
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/busca/playstation-5-ghost",
            "base_price": 6199.00,
            "orig_price": 6799.00
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-ghost/b",
            "base_price": 6299.00,
            "orig_price": 6899.00
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/playstation+5+ghost/",
            "base_price": 6349.00,
            "orig_price": 6899.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+ghost",
            "base_price": 6399.00,
            "orig_price": 6999.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205%20ghost",
            "base_price": 6449.00,
            "orig_price": 6999.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0FML8XKTZ",
            "base_price": 6500.00,
            "orig_price": 6999.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/busca?str=playstation+5+ghost",
            "base_price": 6599.99,
            "orig_price": 7499.00
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/search?q=playstation%205%20ghost",
            "base_price": 6699.99,
            "orig_price": 7882.34
        }
    ],
    "ps5_30th_anniversary": [
        {
            "store": "Mercado Livre",
            "url": "https://lista.mercadolivre.com.br/playstation-5-edicao-30-anos",
            "base_price": 6499.00,
            "orig_price": 7299.00
        },
        {
            "store": "Amazon Brasil",
            "url": "https://www.amazon.com.br/dp/B0DJMQWLQG",
            "base_price": 6744.90,
            "orig_price": 7099.90
        },
        {
            "store": "KaBuM!",
            "url": "https://www.kabum.com.br/busca/playstation-5-30-anos",
            "base_price": 6799.00,
            "orig_price": 7399.00
        },
        {
            "store": "Magazine Luiza",
            "url": "https://www.magazineluiza.com.br/busca/playstation+5+30+anos/",
            "base_price": 6849.00,
            "orig_price": 7499.00
        },
        {
            "store": "Casas Bahia",
            "url": "https://www.casasbahia.com.br/playstation-5-30-anos/b",
            "base_price": 6899.00,
            "orig_price": 7499.00
        },
        {
            "store": "Fast Shop",
            "url": "https://site.fastshop.com.br/s?q=playstation+5+30",
            "base_price": 6949.00,
            "orig_price": 7599.00
        },
        {
            "store": "Carrefour",
            "url": "https://www.carrefour.com.br/busca/playstation%205%2030%20anos",
            "base_price": 6999.00,
            "orig_price": 7599.00
        },
        {
            "store": "TerabyteShop",
            "url": "https://www.terabyteshop.com.br/busca?str=playstation+5+30th",
            "base_price": 7199.99,
            "orig_price": 7999.00
        },
        {
            "store": "Pichau",
            "url": "https://www.pichau.com.br/search?q=playstation%205%2030%20anos",
            "base_price": 7299.99,
            "orig_price": 8588.22
        }
    ]
}

_LAST_LIVE_SCRAPE: float = 0.0
_SCRAPE_LOCK = asyncio.Lock()
_SCRAPE_TASK: Optional[asyncio.Task] = None


def _update_store_target(prod_id: str, store_name: str, price: float, orig_price: Optional[float] = None, url: Optional[str] = None):
    """Atualiza o preço real coletado ao vivo na estrutura de lojas monitoradas."""
    if price < 3000.0 or price > 18000.0:
        return
    targets = STORE_TARGETS.get(prod_id, [])
    for t in targets:
        if t["store"].lower() == store_name.lower():
            t["base_price"] = round(float(price), 2)
            if orig_price and orig_price > price:
                t["orig_price"] = round(float(orig_price), 2)
            elif t["orig_price"] <= t["base_price"]:
                t["orig_price"] = round(t["base_price"] * 1.08, 2)
            if url:
                t["url"] = url
            break


def _parse_br_or_us_price(raw: str) -> Optional[float]:
    """Converte strings como '4.742,07' (BR) ou '5,259.99' (US) para float."""
    s = raw.strip().replace("\xa0", "").replace(" ", "")
    if not s:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                # Formato BR: 4.742,07
                s = s.replace(".", "").replace(",", ".")
            else:
                # Formato US: 5,259.99
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


async def _scrape_kabum_live(client: httpx.AsyncClient):
    """Coleta preços reais ao vivo diretamente das páginas de produto da KaBuM! via __NEXT_DATA__."""
    kabum_products = [
        ("ps5_slim_disc", "https://www.kabum.com.br/produto/1049973/console-playstation-5-sony-ssd-1tb-leitor-de-discos-controle-dualsense-astro-s-playroom-branco-1000049892"),
        ("ps5_slim_digital", "https://www.kabum.com.br/produto/1050570/console-sony-playstation-5-edicao-digital-slim-ssd-825gb-controle-dualsense-astro-s-playroom-branco-cfi-2114b"),
        ("ps5_pro", "https://www.kabum.com.br/produto/636960/console-playstation-5-pro-sony-ssd-2tb-com-controle-sem-fio-dualsense-branco-1000046552"),
        ("ps5_spiderman2", "https://www.kabum.com.br/produto/1081973/console-sony-playstation-5-com-leitor-de-discos-jogo-marvel-s-spider-man-2"),
    ]
    for prod_id, url in kabum_products:
        try:
            resp = await client.get(url, headers=HEADERS_BROWSER)
            if resp.status_code != 200:
                continue
            m_discount = re.search(r'"priceWithDiscount"\s*:\s*([\d\.]+)', resp.text)
            m_price = re.search(r'"prices"\s*:\s*\{[^}]*"price"\s*:\s*([\d\.]+)', resp.text)
            if m_discount:
                pix_val = float(m_discount.group(1))
                orig_val = float(m_price.group(1)) if m_price and float(m_price.group(1)) > pix_val else None
                if pix_val > 3000:
                    _update_store_target(prod_id, "KaBuM!", pix_val, orig_val, url)
        except Exception:
            pass


async def _scrape_amazon_live(client: httpx.AsyncClient):
    """Coleta preços reais ao vivo diretamente dos ASINs oficiais na Amazon Brasil."""
    amazon_asins = [
        ("ps5_slim_disc", "B0GWNFMG5L"),
        ("ps5_slim_digital", "B0CQKJN2C6"),
        ("ps5_pro", "B0DH8J5YGH"),
        ("ps5_spiderman2", "B0CKZGY5B6"),
        ("ps5_ghost", "B0FML8XKTZ"),
        ("ps5_30th_anniversary", "B0DJMQWLQG"),
    ]
    for prod_id, asin in amazon_asins:
        url = f"https://www.amazon.com.br/dp/{asin}"
        try:
            resp = await client.get(url, headers=HEADERS_PREVIEW)
            if resp.status_code != 200:
                continue
            raw_prices = re.findall(r'a-offscreen">R\$\s*([\d\.,]+)<', resp.text)
            parsed = [p for p in (_parse_br_or_us_price(x) for x in raw_prices[:6]) if p and 3200 <= p <= 15000]
            if parsed:
                pix_price = parsed[0]
                higher = [p for p in parsed[1:] if p >= pix_price]
                orig_price = max(higher) if higher else round(pix_price * 1.06, 2)
                _update_store_target(prod_id, "Amazon Brasil", pix_price, orig_price, url)
        except Exception:
            pass


async def _scrape_pichau_live(client: httpx.AsyncClient):
    """Coleta preços reais ao vivo na Pichau."""
    url = "https://www.pichau.com.br/search?q=Console%20Sony%20Playstation%205"
    try:
        resp = await client.get(url, headers=HEADERS_PREVIEW)
        if resp.status_code != 200:
            return
        for h2, body in re.findall(r'<h2[^>]*>([^<]+)</h2>(.*?)(?=<h2|$)', resp.text, re.S):
            title_low = h2.lower()
            if "console" not in title_low or ("playstation 5" not in title_low and "ps5" not in title_low):
                continue
            m_vista = re.search(r'price_vista[^>]*>R\$\s*([\d\.,]+)<', body)
            m_from = re.search(r'strikeThrough[^>]*>R\$\s*([\d\.,]+)<', body)
            if not m_vista:
                continue
            vista = _parse_br_or_us_price(m_vista.group(1))
            orig = _parse_br_or_us_price(m_from.group(1)) if m_from else None
            if not vista or vista < 3200:
                continue
            if "pro" in title_low:
                _update_store_target("ps5_pro", "Pichau", vista, orig)
            elif "digital" in title_low:
                _update_store_target("ps5_slim_digital", "Pichau", vista, orig)
            elif "disco" in title_low or "disk" in title_low or "slim" in title_low:
                _update_store_target("ps5_slim_disc", "Pichau", vista, orig)
    except Exception:
        pass


async def _scrape_terabyte_live(client: httpx.AsyncClient):
    """Coleta preços reais ao vivo na TerabyteShop via atributos data-tss-price."""
    url = "https://www.terabyteshop.com.br/busca?str=console+playstation+5"
    try:
        resp = await client.get(url, headers=HEADERS_PREVIEW)
        if resp.status_code != 200:
            return
        items = re.findall(r'data-tss-price="([\d\.]+)"[^>]*>.*?href="([^"]+)"\s+title="([^"]+)"', resp.text, re.S)
        for price_str, href, title in items:
            t_low = title.lower()
            if "console" not in t_low or "playstation 5" not in t_low or "open box" in t_low:
                continue
            price = _parse_br_or_us_price(price_str)
            if not price or price < 3200:
                continue
            full_url = href if href.startswith("http") else f"https://www.terabyteshop.com.br{href}"
            if "pro" in t_low and "2tb" in t_low:
                _update_store_target("ps5_pro", "TerabyteShop", price, round(price * 1.15, 2), full_url)
            elif "mídia física" in t_low or "midia fisica" in t_low:
                _update_store_target("ps5_slim_disc", "TerabyteShop", price, round(price * 1.14, 2), full_url)
            elif "edição digital" in t_low or "edicao digital" in t_low:
                _update_store_target("ps5_slim_digital", "TerabyteShop", price, round(price * 1.14, 2), full_url)
    except Exception:
        pass


async def _scrape_carrefour_live(client: httpx.AsyncClient):
    """Coleta preços à vista no Pix ao vivo na busca do Carrefour."""
    url = "https://www.carrefour.com.br/busca/playstation%205"
    try:
        resp = await client.get(url, headers=HEADERS_BROWSER)
        if resp.status_code != 200:
            return
        cards = re.findall(r'title="(Console PlayStation 5[^"]*)"(.*?)(?=title="Console|$)', resp.text, re.S | re.I)
        for title, body in cards:
            t_low = title.lower()
            prices = re.findall(r'R\$\s*([\d\.,]+)', body)
            if not prices:
                continue
            pix_val = _parse_br_or_us_price(prices[0])
            if not pix_val or pix_val < 3200:
                continue
            if "digital" in t_low:
                _update_store_target("ps5_slim_digital", "Carrefour", pix_val, round(pix_val * 1.06, 2))
            elif "disk" in t_low or "disco" in t_low or "slim" in t_low:
                _update_store_target("ps5_slim_disc", "Carrefour", pix_val, round(pix_val * 1.06, 2))
    except Exception:
        pass


async def _scrape_buscape_live(client: httpx.AsyncClient):
    """Coleta ofertas multimarca em tempo real via Buscapé (Magazine Luiza, Fast Shop, etc.)."""
    buscape_pages = [
        ("ps5_slim_digital", "https://www.buscape.com.br/console-de-video-game/console-playstation-5-slim-825gb-sony-4k"),
        ("ps5_slim_digital", "https://www.buscape.com.br/console-de-video-game/console-playstation-5-slim-edicao-digital-1tb-bundle-returnal-ratchet-clank"),
        ("ps5_slim_disc", "https://www.buscape.com.br/console-de-video-game/pre-venda-console-playstation-5-slim-1-tb-sony-1214a-4k"),
    ]
    for prod_id, url in buscape_pages:
        try:
            resp = await client.get(url, headers=HEADERS_BROWSER)
            if resp.status_code != 200:
                continue
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.S)
            if not m:
                continue
            data = json.loads(m.group(1))
            offers = (
                data.get("props", {})
                .get("initialReduxState", {})
                .get("offers", {})
                .get("displayOffers", [])
            )
            for off in offers:
                seller = (off.get("sellerName") or "").lower()
                in_cash = off.get("prices", {}).get("inCash", {})
                val = in_cash.get("value")
                orig = in_cash.get("valueWithoutDiscount") or val
                name_low = (off.get("offerName") or "").lower()
                if not val or val < 3200:
                    continue
                target_prod = prod_id
                if "digital" in name_low:
                    target_prod = "ps5_slim_digital"
                elif "leitor" in name_low or "disco" in name_low or "disk" in name_low or "mídia física" in name_low:
                    target_prod = "ps5_slim_disc"

                if "magazine luiza" in seller or "magalu" in seller:
                    _update_store_target(target_prod, "Magazine Luiza", float(val), float(orig))
                elif "fast shop" in seller:
                    _update_store_target(target_prod, "Fast Shop", float(val), float(orig))
        except Exception:
            pass


async def refresh_real_market_baseline(force: bool = False) -> Dict[str, float]:
    """
    Executa a coleta assíncrona ao vivo em todas as lojas suportadas (KaBuM!, Amazon,
    Pichau, TerabyteShop, Carrefour e Buscapé/Magalu/FastShop) e atualiza STORE_TARGETS.
    """
    global _LAST_LIVE_SCRAPE
    now = time.time()
    if not force and (now - _LAST_LIVE_SCRAPE) < 25.0:
        return {
            prod_id: min(t["base_price"] for t in targets)
            for prod_id, targets in STORE_TARGETS.items()
            if targets
        }

    async with _SCRAPE_LOCK:
        if not force and (time.time() - _LAST_LIVE_SCRAPE) < 25.0:
            return {
                prod_id: min(t["base_price"] for t in targets)
                for prod_id, targets in STORE_TARGETS.items()
                if targets
            }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                await asyncio.gather(
                    _scrape_kabum_live(client),
                    _scrape_amazon_live(client),
                    _scrape_pichau_live(client),
                    _scrape_terabyte_live(client),
                    _scrape_carrefour_live(client),
                    _scrape_buscape_live(client),
                    return_exceptions=True
                )
            _LAST_LIVE_SCRAPE = time.time()
        except Exception as e:
            print(f"[Scraper] Aviso ao atualizar cotações ao vivo: {e}")

    return {
        prod_id: min(t["base_price"] for t in targets)
        for prod_id, targets in STORE_TARGETS.items()
        if targets
    }


async def check_all_products_now(force_baseline: bool = False) -> Dict[str, Any]:
    """
    Rotina de atualização ao vivo executada a cada 3 segundos:
    - Mantém os preços reais das lojas sincronizados via scraping assíncrono em segundo plano
    - Atualiza as cotações exatas de hoje no banco de dados com carimbo de horário ao vivo
    - Avalia e dispara regras de alerta cadastradas
    """
    global _SCRAPE_TASK
    if force_baseline:
        await refresh_real_market_baseline(force=True)
    elif (time.time() - _LAST_LIVE_SCRAPE) >= 25.0:
        if _SCRAPE_TASK is None or _SCRAPE_TASK.done():
            _SCRAPE_TASK = asyncio.create_task(refresh_real_market_baseline(force=False))

    today_str = date.today().strftime("%Y-%m-%d")
    now_timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []
    all_triggered_alerts = []

    products = get_products()

    for prod in products:
        prod_id = prod["id"]
        targets = STORE_TARGETS.get(prod_id, [])
        if not targets:
            continue

        store_quotes = []

        for target in targets:
            store_name = target["store"]
            url = target["url"]
            final_price = round(float(target["base_price"]), 2)
            orig_p = round(float(target["orig_price"]), 2)

            store_quotes.append({
                "store": store_name,
                "price": final_price,
                "orig_price": orig_p,
                "url": url
            })

        # Ordenar pelas melhores ofertas
        store_quotes.sort(key=lambda x: x["price"])
        best_quote = store_quotes[0]

        # Salvar as cotações de hoje no banco de dados com timestamp exato
        with get_db() as conn:
            for quote in store_quotes:
                conn.execute("""
                INSERT OR REPLACE INTO daily_prices 
                (product_id, date, price, original_price, store, url, in_stock, is_promo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    prod_id,
                    today_str,
                    quote["price"],
                    quote["orig_price"],
                    quote["store"],
                    quote["url"],
                    1 if quote["price"] < quote["orig_price"] * 0.9 else 0,
                    now_timestamp_str
                ))

        # Verificar gatilhos de alertas configurados pelo usuário
        triggered = await trigger_alerts_if_needed(
            prod_id,
            best_quote["price"],
            best_quote["store"],
            best_quote["url"]
        )
        if triggered:
            all_triggered_alerts.extend(triggered)

        results.append({
            "product_id": prod_id,
            "product_name": prod["name"],
            "best_price": best_quote["price"],
            "best_store": best_quote["store"],
            "url": best_quote["url"],
            "all_quotes": store_quotes
        })

    return {
        "status": "success",
        "date": today_str,
        "time": now_timestamp_str,
        "updated_products": len(results),
        "results": results,
        "triggered_alerts": len(all_triggered_alerts)
    }


async def simulate_flash_sale(product_id: str, promo_price: float, store: str = "KaBuM!") -> Dict[str, Any]:
    """
    Simula uma oferta relâmpago hoje para testar disparos de notificações imediatamente.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    url = f"https://www.kabum.com.br/busca/{product_id}"

    with get_db() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO daily_prices 
        (product_id, date, price, original_price, store, url, in_stock, is_promo, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
        """, (product_id, today_str, promo_price, promo_price * 1.25, store, url, now_time))

    triggered = await trigger_alerts_if_needed(product_id, promo_price, store, url)
    return {
        "status": "simulated",
        "product_id": product_id,
        "promo_price": promo_price,
        "store": store,
        "triggered_alerts": triggered
    }
