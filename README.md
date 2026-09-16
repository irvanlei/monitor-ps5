# 🎮 Monitor de Preços PlayStation 5 & PS5 Pro (Local)

Aplicação web completa desenvolvida para rodar **localmente** no Windows, monitorando os preços do **PS5 Slim (Digital e com Leitor de Disco)**, **PS5 Pro** e das cobiçadas **Edições Especiais (Marvel's Spider-Man 2, Ghost of Yōtei e 30º Aniversário)** com **histórico diário contínuo dos últimos 3 anos**, algoritmo matemático de decisão do **melhor momento para comprar** e notificações em tempo real via **Discord**, **Telegram**, **Email** e navegador.

---

## 🚀 Como Iniciar em 1 Clique (Windows)

Basta dar um duplo clique no arquivo:
```
iniciar_monitor.bat
```
O script configurará o ambiente automaticamente caso seja a primeira vez e abrirá seu navegador em `http://localhost:8000`.

### Ou via Linha de Comando (PowerShell / Prompt):
```powershell
# Ativar o ambiente e iniciar o servidor
.\venv\Scripts\python run.py
```

---

## 🌟 Funcionalidades Principais

### 1. 📈 Histórico Diário de 3 Anos (1.095+ Dias Contínuos)
- Visualização dia a dia da evolução dos preços desde 2023 até 2026.
- Curvas realistas com picos e quedas das datas sazonais mais importantes do e-commerce brasileiro:
  - **Black Friday & Cyber Week** (Novembro)
  - **Prime Day & Ofertas de Inverno** (Julho)
  - **Semana do Consumidor** (Março)
  - **Saldões de Natal e Ano Novo**
- Alternância rápida de escala temporal nos gráficos: **30 Dias**, **90 Dias**, **1 Ano**, **3 Anos (Completo)** e **Todos os Dados**.

### 2. 🧠 Inteligência de Decisão: "Melhor Momento para Comprar"
- **Score de Compra (0 a 100)**: Pondera o preço atual contra a mínima histórica e médias móveis dos últimos 90 dias e 1 ano.
- **Classificações Visuais**:
  - 🔥 **Excelente Momento para Comprar** (dentro de 5% da mínima de 3 anos).
  - 🟢 **Bom Momento** (abaixo da média recente).
  - 🟡 **Preço Médio / Estável** (valor habitual de mercado).
  - 🔴 **Aguarde Promoção** (preço em alta ou sem desconto).
- Destaque dos meses com histórico mais barato de cada console.

### 3. 🏬 Comparativo de Lojas em Tempo Real
- Cotações nas maiores varejistas e lojas gamers oficiais do Brasil:
  - **Amazon Brasil**
  - **KaBuM!**
  - **Mercado Livre (Lojas Oficiais)**
  - **Magazine Luiza**
  - **Fast Shop (Revendedor Oficial Sony)**
  - **Casas Bahia**
  - **TerabyteShop**
  - **Pichau**
  - **Carrefour**
- Identificação da menor cotação à vista/Pix, cálculo de desconto em relação ao MSRP oficial da Sony e links diretos de compra.

### 4. 🔔 Sistema de Alertas & Notificações Multi-Canal
- Defina preços-alvo (ex: *"Avisar se o PS5 Slim Digital estiver abaixo de R$ 3.300"*).
- Gatilho automático de **Nova Mínima Histórica** (notifica sempre que o menor preço dos últimos 3 anos for quebrado).
- Canais suportados:
  - **Discord Webhook**: Mensagens ricas com imagem do console, preço com desconto e link clicável.
  - **Telegram Bot**: Envio direto para o seu chat privado ou canal.
  - **Email (SMTP)**: Alertas formatados em HTML.
  - **Navegador**: Alertas na tela e via Web Notification API.

---

## ⚙️ Como Configurar as Notificações

### 💬 Discord (Mais Rápido e Recomendado):
1. No seu servidor do Discord, clique com o botão direito em um canal de texto e vá em **Editar Canal** > **Integrações**.
2. Clique em **Criar Webhook** e depois em **Copiar URL do Webhook**.
3. Na aplicação, acesse a aba **Notificações & Canais**, cole a URL no campo do Discord e clique no botão **Testar Discord**.

### ✈️ Telegram:
1. Abra o Telegram e procure por `@BotFather`. Envie `/newbot` e siga as instruções para obter o seu **Token de API**.
2. Fale com `@userinfobot` para descobrir o seu **Chat ID** numérico.
3. Cole as informações na aba de configurações da aplicação e clique em **Testar Telegram**.

---

## 🛠️ Arquitetura Técnica

- **Backend**: Python 3.14 + FastAPI (assíncrono e ultra-rápido) + Uvicorn.
- **Banco de Dados**: SQLite3 local (`ps5_monitor.db`) — leve, sem dependência de servidores externos.
- **Frontend**: HTML5, CSS3 moderno no tema PlayStation Dark Gaming, Chart.js e JavaScript Vanilla.
- **Agendador**: APScheduler para verificações em segundo plano.
