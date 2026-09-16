"""
Script de Validação e Testes Automatizados dos Endpoints
"""
import sys
from fastapi.testclient import TestClient
from app.main import app

# Forçar saída utf-8
sys.stdout.reconfigure(encoding='utf-8')

client = TestClient(app)

def run_tests():
    print("Iniciando bateria de testes...")
    
    # 1. Rota raiz /
    r = client.get('/')
    assert r.status_code == 200, f"Falha na home: {r.status_code}"
    assert "PS5 Tracker" in r.text
    print("✓ [OK] GET / (Dashboard HTML renderizado com sucesso)")
    
    # 2. Rota de produtos /api/products
    r = client.get('/api/products')
    assert r.status_code == 200
    products = r.json()
    assert len(products) == 6, f"Esperado 6 consoles, recebido {len(products)}"
    print(f"✓ [OK] GET /api/products (6 consoles monitorados: {[p['product']['name'] for p in products]})")
    
    # 3. Rota de detalhes e veredito do Spider-Man 2 e PS5 Pro
    r = client.get('/api/product/ps5_spiderman2')
    assert r.status_code == 200
    sm = r.json()
    print(f"✓ [OK] GET /api/product/ps5_spiderman2 (Preço: R$ {sm['current']['price']:,.2f} | Score: {sm['recommendation']['score']}/100 | {sm['recommendation']['badge']})")
    
    r = client.get('/api/product/ps5_ghost')
    assert r.status_code == 200
    gh = r.json()
    print(f"✓ [OK] GET /api/product/ps5_ghost (Preço: R$ {gh['current']['price']:,.2f} | Score: {gh['recommendation']['score']}/100 | {gh['recommendation']['badge']})")
    
    # 4. Rota da série temporal diária a partir do lançamento no Brasil
    r = client.get('/api/history/ps5_slim_disc?range=launch')
    assert r.status_code == 200
    hist = r.json()
    total_days = len(hist["prices"])
    assert hist["release_date"] == "2024-04-17", f"Data incorreta: {hist.get('release_date')}"
    assert hist["start_date"] == "2024-04-17", f"Início incorreto: {hist.get('start_date')}"
    assert total_days >= 850, f"Poucos pontos: {total_days}"
    print(f"✓ [OK] GET /api/history/ps5_slim_disc?range=launch (Início no lançamento oficial BR: {hist['release_date_br']} | {total_days} dias contínuos carregados)")
    
    # 5. Rota de criação e exclusão de alertas
    payload = {
        "product_id": "ps5_slim_digital",
        "target_price": 3299.00,
        "alert_on_all_time_low": True,
        "channel": "discord"
    }
    r = client.post('/api/alerts', json=payload)
    assert r.status_code == 200
    alert_id = r.json()["id"]
    print(f"✓ [OK] POST /api/alerts (Alerta cadastrado com ID {alert_id})")
    
    # Listar alertas
    r = client.get('/api/alerts')
    assert r.status_code == 200
    assert any(a["id"] == alert_id for a in r.json())
    print(f"✓ [OK] GET /api/alerts (Alerta verificado na listagem)")
    
    # Deletar alerta de teste
    r = client.delete(f'/api/alerts/{alert_id}')
    assert r.status_code == 200
    print(f"✓ [OK] DELETE /api/alerts/{alert_id} (Alerta excluído com sucesso)")
    
    # 6. Rota de comparação de lojas
    r = client.get('/api/stores/ps5_slim_disc')
    assert r.status_code == 200
    stores = r.json()
    assert len(stores) > 0
    print(f"✓ [OK] GET /api/stores/ps5_slim_disc ({len(stores)} lojas com cotação: {[s['store'] for s in stores]})")
    
    # 7. Rota de configurações
    r = client.get('/api/settings')
    assert r.status_code == 200
    print("✓ [OK] GET /api/settings (Configurações lidas com sucesso)")
    
    # 8. Validação das Fotografias Oficiais dos 6 Consoles
    photo_files = [
        "ps5_slim_digital.png",
        "ps5_slim_disc.png",
        "ps5_pro.png",
        "ps5_spiderman2.png",
        "ps5_ghost.png",
        "ps5_30th_anniversary.png"
    ]
    for photo in photo_files:
        r = client.get(f'/static/img/{photo}')
        assert r.status_code == 200, f"Erro ao carregar /static/img/{photo}"
        assert len(r.content) > 1000, f"Arquivo /static/img/{photo} muito pequeno ou corrompido"
        print(f"✓ [OK] GET /static/img/{photo} ({len(r.content):,} bytes carregados com sucesso)")
    
    print("\n🎉 TODOS OS TESTES PASSARAM COM 100% DE SUCESSO!")

if __name__ == "__main__":
    run_tests()
