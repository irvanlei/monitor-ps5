"""
Gestão do Banco de Dados SQLite para o Monitor de Preços do PS5
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ps5_monitor.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Inicializa as tabelas do banco de dados se não existirem."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tabela de Produtos com data oficial de lançamento no Brasil
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            edition TEXT NOT NULL,
            description TEXT,
            msrp REAL NOT NULL,
            image_url TEXT,
            release_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Migração defensiva caso a tabela já exista sem release_date
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        if "release_date" not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN release_date TEXT")

        # 2. Tabela de Preços Diários (Histórico dia a dia desde o lançamento)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            date TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            store TEXT NOT NULL,
            url TEXT,
            in_stock INTEGER DEFAULT 1,
            is_promo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(product_id, date, store)
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_lookup ON daily_prices(product_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date)")
        
        # 3. Tabela de Metas / Alertas de Preço
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            target_price REAL NOT NULL,
            alert_on_all_time_low INTEGER DEFAULT 1,
            channel TEXT DEFAULT 'all',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_triggered_at TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """)
        
        # 4. Tabela de Configurações (Webhooks, Tokens, Preferências)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        
        # 5. Tabela de Logs de Notificações
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            price REAL,
            channel TEXT,
            status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
            
        # Inserção de produtos padrão caso não existam
        default_products = [
            (
                "ps5_slim_digital",
                "PlayStation 5 Slim - Edição Digital",
                "Digital",
                "Console PS5 Slim sem leitor de disco, 1TB SSD, controle DualSense branco.",
                3999.90,
                "/static/img/ps5_slim_digital.png",
                "2024-01-23"
            ),
            (
                "ps5_slim_disc",
                "PlayStation 5 Slim - Edição com Leitor de Disco",
                "Disco Físico",
                "Console PS5 Slim com leitor de mídia física Blu-ray 4K Ultra HD, 1TB SSD.",
                4499.90,
                "/static/img/ps5_slim_disc.png",
                "2024-04-17"
            ),
            (
                "ps5_pro",
                "PlayStation 5 Pro",
                "Pro 2TB",
                "Console PS5 Pro com GPU avançada, Ray Tracing aprimorado e PlayStation Spectral Super Resolution (PSSR), 2TB SSD.",
                6999.90,
                "/static/img/ps5_pro.png",
                "2024-11-07"
            ),
            (
                "ps5_spiderman2",
                "PlayStation 5 - Edição Limitada Marvel's Spider-Man 2",
                "Edição Limitada (Spider-Man)",
                "Console PS5 Edição Limitada Marvel's Spider-Man 2 com tampas temáticas do Simbionte e controle DualSense exclusivo.",
                4999.90,
                "/static/img/ps5_spiderman2.png",
                "2023-10-20"
            ),
            (
                "ps5_ghost",
                "PlayStation 5 - Edição Especial Ghost of Yōtei",
                "Edição Especial (Ghost)",
                "Console PS5 comemorativo temático inspirado na saga Ghost (Ghost of Yōtei / Tsushima) com controle DualSense temático.",
                4699.90,
                "/static/img/ps5_ghost.png",
                "2024-09-24"
            ),
            (
                "ps5_30th_anniversary",
                "PlayStation 5 Slim - Edição 30º Aniversário",
                "Edição 30º Aniversário",
                "Console PS5 Slim de colecionador na cor cinza clássica retrô do PlayStation 1 original, cabos comemorativos e DualSense especial.",
                4499.90,
                "/static/img/ps5_30th_anniversary.png",
                "2024-11-21"
            )
        ]
        
        cursor.executemany("""
        INSERT OR IGNORE INTO products (id, name, edition, description, msrp, image_url, release_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, default_products)
        
        # Atualizar datas oficiais de lançamento no Brasil para todos os consoles existentes
        official_launch_dates = {
            "ps5_slim_digital": "2024-01-23",
            "ps5_slim_disc": "2024-04-17",
            "ps5_pro": "2024-11-07",
            "ps5_spiderman2": "2023-10-20",
            "ps5_ghost": "2024-09-24",
            "ps5_30th_anniversary": "2024-11-21"
        }
        for prod_id, r_date in official_launch_dates.items():
            cursor.execute("UPDATE products SET release_date = ? WHERE id = ?", (r_date, prod_id))
        
        # Configurações padrão
        default_settings = [
            ("discord_webhook_url", ""),
            ("telegram_bot_token", ""),
            ("telegram_chat_id", ""),
            ("email_smtp_host", "smtp.gmail.com"),
            ("email_smtp_port", "587"),
            ("email_user", ""),
            ("email_password", ""),
            ("email_recipient", ""),
            ("check_interval_hours", "6"),
            ("notify_browser", "1"),
            ("notify_discord", "1"),
            ("notify_telegram", "1")
        ]
        
        cursor.executemany("""
        INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        """, default_settings)

def get_products() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY msrp ASC").fetchall()
        return [dict(row) for row in rows]

def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None

def get_settings() -> Dict[str, str]:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

def update_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

def get_alerts() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, p.name as product_name, p.edition 
            FROM alerts a
            JOIN products p ON a.product_id = p.id
            ORDER BY a.created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]

def add_alert(product_id: str, target_price: float, alert_on_all_time_low: bool = True, channel: str = "all") -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO alerts (product_id, target_price, alert_on_all_time_low, channel)
            VALUES (?, ?, ?, ?)
        """, (product_id, target_price, 1 if alert_on_all_time_low else 0, channel))
        return cursor.lastrowid

def delete_alert(alert_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

def log_notification(product_id: str, price: float, channel: str, status: str, message: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO notification_logs (product_id, price, channel, status, message)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, price, channel, status, message))

def get_notification_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT l.*, p.name as product_name
            FROM notification_logs l
            LEFT JOIN products p ON l.product_id = p.id
            ORDER BY l.created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]
