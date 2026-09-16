/**
 * PS5 Tracker Pro - Lógica Frontend
 * Chart.js, filtros de período (30d, 90d, 1y, 3y, all),
 * alertas de preço, comparações de lojas e atualizações em tempo real (3s).
 */

let selectedProductId = "ps5_slim_disc";
let selectedRange = "launch";
let priceChart = null;
let currentProducts = [];
let isRealtimeActive = true;
let realtimeCountdown = 3;
let realtimeTimerId = null;
let lastKnownPrices = {};

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    requestBrowserNotificationPermission();
});

async function initApp() {
    await loadProducts();
    await loadSettings();
    await loadAlerts();
    startRealtimeLoop();
}

function playPriceAlertSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
        osc.frequency.setValueAtTime(880.00, audioCtx.currentTime + 0.1); // A5
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {}
}

function startRealtimeLoop() {
    if (realtimeTimerId) clearInterval(realtimeTimerId);
    
    realtimeTimerId = setInterval(async () => {
        if (!isRealtimeActive) return;
        
        realtimeCountdown--;
        const countdownEl = document.getElementById("countdown-text");
        if (countdownEl) countdownEl.textContent = `${realtimeCountdown}s`;
        
        if (realtimeCountdown <= 0) {
            realtimeCountdown = 3;
            await performRealtimeTick();
        }
    }, 1000);
}

function toggleRealtimeMode(isActive) {
    isRealtimeActive = isActive;
    const pill = document.getElementById("realtime-pill");
    const countdownEl = document.getElementById("countdown-text");
    if (pill) {
        if (isActive) {
            pill.classList.remove("paused");
            realtimeCountdown = 3;
            if (countdownEl) countdownEl.textContent = "3s";
            showToast("⚡ Atualização em tempo real (3s) ativada!", "success");
        } else {
            pill.classList.add("paused");
            if (countdownEl) countdownEl.textContent = "Pausado";
            showToast("⏸️ Atualização automática pausada.", "info");
        }
    }
}

async function performRealtimeTick() {
    try {
        // Dispara checagem rápida no backend
        const checkResp = await fetch("/api/check-now", { method: "POST" });
        const checkData = await checkResp.json();
        
        // Atualiza a lista de produtos e detecta mudanças de preço
        const resp = await fetch("/api/products");
        const products = await resp.json();
        
        let priceChanged = false;
        
        products.forEach(p => {
            const prodId = p.product.id;
            const newPrice = p.current ? p.current.price : 0;
            const oldPrice = lastKnownPrices[prodId];
            
            if (oldPrice && Math.abs(oldPrice - newPrice) > 0.05) {
                priceChanged = true;
                const priceEl = document.querySelector(`#card-${prodId} .model-current-price`);
                if (priceEl) {
                    priceEl.textContent = `R$ ${newPrice.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                    priceEl.classList.remove("price-flash-drop", "price-flash-rise");
                    void priceEl.offsetWidth; // reflow
                    priceEl.classList.add(newPrice < oldPrice ? "price-flash-drop" : "price-flash-rise");
                }
                
                const storeBadge = document.querySelector(`#card-${prodId} .store-badge`);
                if (storeBadge && p.current) {
                    storeBadge.innerHTML = `Melhor cotação: <strong>${p.current.store}</strong>`;
                }
            }
            lastKnownPrices[prodId] = newPrice;
        });
        
        if (priceChanged) {
            playPriceAlertSound();
            await updateProductDetailsQuiet(selectedProductId);
        }
        
        // Atualiza carimbo de última checagem
        const now = new Date();
        const timeStr = now.toLocaleTimeString('pt-BR');
        const updateText = document.getElementById("last-update-text");
        if (updateText) updateText.textContent = `${timeStr} (ao vivo)`;
        
        if (checkData && checkData.triggered_alerts > 0) {
            showToast(`🔥 ${checkData.triggered_alerts} Alerta(s) de Preço Ativado(s)!`, "info");
            playPriceAlertSound();
            loadAlerts();
            loadLogs();
        }
        
    } catch (err) {
        console.warn("Tick em tempo real:", err);
    }
}

async function updateProductDetailsQuiet(productId) {
    try {
        const resp = await fetch(`/api/product/${productId}`);
        const data = await resp.json();
        
        const rec = data.recommendation;
        const extremes = data.history_extremes;
        const current = data.current;
        const averages = data.averages;
        const prod = data.product;

        const recBadge = document.getElementById("rec-badge");
        if (recBadge) {
            recBadge.textContent = rec.badge;
            recBadge.style.color = rec.color;
            recBadge.style.borderColor = rec.color;
        }

        const scoreCircle = document.getElementById("rec-score-circle");
        if (scoreCircle) scoreCircle.style.borderColor = rec.color;
        const scoreVal = document.getElementById("rec-score-value");
        if (scoreVal) scoreVal.textContent = rec.score;

        const recText = document.getElementById("rec-text");
        if (recText) recText.textContent = rec.explanation;

        // Se a aba de lojas estiver aberta, atualiza a tabela de lojas
        const storesTab = document.getElementById("tab-stores");
        if (storesTab && storesTab.classList.contains("active")) {
            await loadStoreComparisons(productId);
        }
    } catch (e) {}
}

// 1. Carregamento de Produtos e Cards
async function loadProducts() {
    try {
        const resp = await fetch("/api/products");
        const products = await resp.json();
        currentProducts = products;

        const container = document.getElementById("models-container");
        container.innerHTML = "";

        products.forEach(p => {
            const prod = p.product;
            const current = p.current || {};
            const rec = p.recommendation || {};

            const card = document.createElement("div");
            card.className = `model-card ${prod.id === selectedProductId ? 'active' : ''}`;
            card.id = `card-${prod.id}`;
            card.onclick = () => selectProduct(prod.id);

            card.innerHTML = `
                <div class="model-top">
                    <div class="model-img-box">
                        <img src="${prod.image_url}" alt="${prod.name}" class="model-img" onerror="this.src='https://placehold.co/80x80/0e1526/ffffff?text=PS5'">
                    </div>
                    <div class="model-info">
                        <span class="model-edition-badge">${prod.edition}</span>
                        <h3 class="model-name">${prod.name}</h3>
                        <div class="model-pricing">
                            <span class="model-current-price">R$ ${current.price ? current.price.toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '--'}</span>
                            <span class="model-msrp">R$ ${prod.msrp.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
                        </div>
                    </div>
                </div>
                <div class="model-footer">
                    <span class="store-badge">Melhor cotação: <strong>${current.store || 'Amazon'}</strong></span>
                    <span class="model-discount-pill">${current.discount_from_msrp_pct || 0}% OFF</span>
                </div>
            `;
            container.appendChild(card);
        });

        // Preencher abas de modelos no Comparativo de Lojas com mini-ícones
        const storesTabs = document.getElementById("stores-model-tabs");
        if (storesTabs) {
            storesTabs.innerHTML = "";
            products.forEach(p => {
                const prod = p.product;
                const chip = document.createElement("button");
                chip.type = "button";
                chip.className = `filter-chip ${prod.id === selectedProductId ? 'active' : ''}`;
                chip.id = `store-tab-${prod.id}`;
                chip.onclick = () => selectProduct(prod.id);
                chip.innerHTML = `
                    <img src="${prod.image_url}" class="chip-img" alt="${prod.name}" onerror="this.style.display='none'">
                    <span>${prod.edition}</span>
                `;
                storesTabs.appendChild(chip);
            });
        }

        // Carregar detalhes do produto selecionado
        await updateProductDetails(selectedProductId);

    } catch (err) {
        console.error("Erro ao carregar produtos:", err);
        showToast("Falha ao comunicar com a API local.", "error");
    }
}

// 2. Seleção de Console
async function selectProduct(productId) {
    selectedProductId = productId;

    // Atualizar classe ativa dos cards superiores
    document.querySelectorAll(".model-card").forEach(c => c.classList.remove("active"));
    const activeCard = document.getElementById(`card-${productId}`);
    if (activeCard) activeCard.classList.add("active");

    // Atualizar chips das abas de lojas
    document.querySelectorAll("#stores-model-tabs .filter-chip").forEach(t => t.classList.remove("active"));
    const activeChip = document.getElementById(`store-tab-${productId}`);
    if (activeChip) activeChip.classList.add("active");

    // Atualizar IMEDIATAMENTE a tabela de lojas para o produto clicado
    loadStoreComparisons(productId);

    // Atualizar detalhes e gráfico
    await updateProductDetails(productId);
}

// 3. Atualizar Análise de Decisão e Gráfico
async function updateProductDetails(productId) {
    try {
        const resp = await fetch(`/api/product/${productId}`);
        const data = await resp.json();

        // Atualizar Card de Decisão de Compra
        const rec = data.recommendation;
        const extremes = data.history_extremes;
        const current = data.current;
        const averages = data.averages;
        const prod = data.product;

        // Atualizar thumbnail e título do console no card de inteligência
        const recImg = document.getElementById("rec-console-img");
        if (recImg && prod.image_url) {
            recImg.src = prod.image_url;
            recImg.alt = prod.name;
        }

        const headingTitle = document.getElementById("rec-heading-title");
        if (headingTitle) {
            headingTitle.textContent = `Análise: ${prod.name}`;
        }

        // Badge e Score
        const recBadge = document.getElementById("rec-badge");
        recBadge.textContent = rec.badge;
        recBadge.style.color = rec.color;
        recBadge.style.borderColor = rec.color;

        const scoreCircle = document.getElementById("rec-score-circle");
        scoreCircle.style.borderColor = rec.color;
        document.getElementById("rec-score-value").textContent = rec.score;

        document.getElementById("rec-text").textContent = rec.explanation;

        // Métricas nos blocos
        document.getElementById("rec-stat-min").textContent = `R$ ${extremes.min_price.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        document.getElementById("rec-stat-min-date").textContent = `em ${formatDateBR(extremes.min_date)} (${extremes.min_store})`;

        document.getElementById("rec-stat-avg90").textContent = `R$ ${averages.avg_90d.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        const diffAvg = data.differences.diff_from_avg90_pct;
        document.getElementById("rec-stat-diff-avg").textContent = `${diffAvg > 0 ? '+' : ''}${diffAvg}% em relação aos 90d`;

        document.getElementById("rec-stat-msrp").textContent = `R$ ${prod.msrp.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        document.getElementById("rec-stat-savings").textContent = `Economia de R$ ${current.savings_vs_msrp.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;

        const launchDateEl = document.getElementById("rec-stat-launch-date");
        if (launchDateEl) {
            launchDateEl.textContent = prod.release_date_br || formatDateBR(prod.release_date);
        }
        const launchInfoEl = document.getElementById("rec-stat-launch-info");
        if (launchInfoEl) {
            launchInfoEl.textContent = "Estreia oficial no Brasil";
        }

        const releaseBr = prod.release_date_br || formatDateBR(prod.release_date);
        const subTitleEl = document.getElementById("chart-product-subtitle");
        if (subTitleEl) {
            subTitleEl.textContent = `${prod.name} • Linha do tempo desde o lançamento no Brasil (${releaseBr})`;
        }

        // Carregar gráfico histórico de forma isolada
        try {
            await loadChartHistory(productId, selectedRange);
        } catch (chartErr) {
            console.warn("Aviso ao atualizar gráfico:", chartErr);
        }

        // Atualizar tabela de lojas
        try {
            await loadStoreComparisons(productId);
        } catch (storeErr) {
            console.warn("Aviso ao atualizar lojas:", storeErr);
        }

    } catch (err) {
        console.error("Erro ao carregar detalhes do produto:", err);
    }
}

// 4. Carregar Gráfico Chart.js
async function loadChartHistory(productId, rangeKey) {
    try {
        const resp = await fetch(`/api/history/${productId}?range=${rangeKey}`);
        const history = await resp.json();

        // Atualizar rodapé do gráfico com métricas do período
        document.getElementById("period-min-price").textContent = `R$ ${history.stats.min.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        document.getElementById("period-avg-price").textContent = `R$ ${history.stats.avg.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        document.getElementById("period-max-price").textContent = `R$ ${history.stats.max.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        document.getElementById("period-total-points").textContent = `${history.total_points} dias registrados`;

        const releaseBr = history.release_date_br || formatDateBR(history.release_date);
        const subTitleEl = document.getElementById("chart-product-subtitle");
        if (subTitleEl && releaseBr) {
            subTitleEl.textContent = `${prodNameFromId(productId)} • Histórico diário desde o lançamento no Brasil (${releaseBr}) • ${history.total_points} dias`;
        }

        renderChart(history);
    } catch (err) {
        console.error("Erro ao carregar série histórica:", err);
    }
}

function prodNameFromId(id) {
    const found = currentProducts.find(p => p.product && p.product.id === id);
    return found ? found.product.name : "PlayStation 5";
}

function renderChart(history) {
    const ctx = document.getElementById("priceHistoryChart").getContext("2d");

    if (priceChart) {
        priceChart.destroy();
    }

    // Criar gradiente sob a linha de preço
    const gradient = ctx.createLinearGradient(0, 0, 0, 360);
    gradient.addColorStop(0, "rgba(0, 112, 209, 0.45)");
    gradient.addColorStop(1, "rgba(0, 112, 209, 0.0)");

    // Linha de média histórica de referência
    const avgLineData = Array(history.labels.length).fill(history.stats.avg);
    const minLineData = Array(history.labels.length).fill(history.stats.min);

    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: history.labels,
            datasets: [
                {
                    label: "Preço no Dia (R$)",
                    data: history.prices,
                    borderColor: "#0070d1",
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.15,
                    pointRadius: history.prices.length > 100 ? 0 : 3,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: "#38bdf8",
                    pointHoverBorderColor: "#ffffff",
                    pointHoverBorderWidth: 2
                },
                {
                    label: "Média do Período",
                    data: avgLineData,
                    borderColor: "rgba(245, 158, 11, 0.7)",
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: "Mínima Histórica",
                    data: minLineData,
                    borderColor: "rgba(16, 185, 129, 0.8)",
                    borderWidth: 1.5,
                    borderDash: [3, 3],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: "top",
                    labels: {
                        color: "#94a3b8",
                        font: { family: "'Plus Jakarta Sans', sans-serif", size: 12 },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(14, 21, 38, 0.95)",
                    titleColor: "#f8fafc",
                    bodyColor: "#cbd5e1",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        title: (items) => {
                            if (!items.length) return "";
                            return `Data: ${formatDateBR(items[0].label)}`;
                        },
                        label: (item) => {
                            const index = item.dataIndex;
                            const storeName = history.stores ? history.stores[index] : "";
                            const promoTag = history.is_promo && history.is_promo[index] ? " 🔥 [PROMOÇÃO]" : "";
                            if (item.datasetIndex === 0) {
                                return ` Preço: R$ ${item.raw.toLocaleString('pt-BR', {minimumFractionDigits: 2})} na ${storeName}${promoTag}`;
                            }
                            return ` ${item.dataset.label}: R$ ${item.raw.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#64748b",
                        font: { size: 11 },
                        maxTicksLimit: 12,
                        callback: function(val, index) {
                            const label = this.getLabelForValue(val);
                            return formatDateBR(label, true);
                        }
                    }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: {
                        color: "#64748b",
                        font: { size: 11 },
                        callback: (val) => `R$ ${val.toLocaleString('pt-BR')}`
                    }
                }
            }
        }
    });
}

function changeChartRange(rangeKey) {
    selectedRange = rangeKey;
    document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
    event.target.classList.add("active");
    loadChartHistory(selectedProductId, rangeKey);
}

// 5. Comparativo de Lojas
async function loadStoreComparisons(productId) {
    try {
        const resp = await fetch(`/api/stores/${productId}`);
        const stores = await resp.json();
        const tbody = document.getElementById("stores-table-body");
        tbody.innerHTML = "";

        if (!stores.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Nenhuma cotação registrada recentemente.</td></tr>`;
            return;
        }

        stores.forEach(s => {
            const discount = s.original_price ? Math.round(((s.original_price - s.price) / s.original_price) * 100) : 0;
            const tr = document.createElement("tr");
            const timeDisplay = s.time ? `${s.time}` : new Date().toLocaleTimeString('pt-BR');
            const isVerifiedDirect = ["Mercado Livre", "KaBuM!", "Pichau"].includes(s.store);
            const verifiedBadge = isVerifiedDirect
                ? `<span style="display: inline-flex; align-items: center; gap: 3px; font-size: 0.7rem; font-weight: 600; color: #10b981; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px; margin-left: 6px;" title="Link direto e verificado para o anúncio do console"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg> Verificado</span>`
                : '';

            tr.innerHTML = `
                <td>
                    <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
                        <strong>${s.store}</strong>
                        ${verifiedBadge}
                    </div>
                </td>
                <td><span class="text-success" style="font-weight: 800; font-size: 1.1rem;">R$ ${s.price.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span></td>
                <td><span class="text-muted" style="text-decoration: line-through;">R$ ${s.original_price ? s.original_price.toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '--'}</span></td>
                <td><span class="model-discount-pill">${discount}% OFF</span></td>
                <td><span class="status-dot"></span> Em Estoque</td>
                <td>
                    <span style="font-weight: 700; color: #10b981;">Hoje</span> às ${timeDisplay}
                    <small style="color: #38bdf8; font-size: 0.75rem; display: block;">(Ao Vivo • 3s)</small>
                </td>
                <td>
                    <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-primary" style="display: inline-flex; align-items: center; gap: 4px;">
                        Ver Oferta
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
                    </a>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error("Erro ao carregar comparativo de lojas:", err);
    }
}

// 6. Abas
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    event.currentTarget.classList.add("active");
    const activeSection = document.getElementById(`tab-${tabId}`);
    if (activeSection) {
        activeSection.classList.add("active");
    }

    if (tabId === "stores") {
        loadStoreComparisons(selectedProductId);
    } else if (tabId === "alerts") {
        loadAlerts();
    } else if (tabId === "settings") {
        loadSettings();
    } else if (tabId === "logs") {
        loadLogs();
    }
}

// 7. Ação: Verificar Preços Agora
async function triggerPriceCheck() {
    const btn = document.getElementById("btn-check-now");
    btn.disabled = true;
    btn.innerHTML = `<span>Verificando...</span>`;

    try {
        const resp = await fetch("/api/check-now", { method: "POST" });
        const data = await resp.json();

        showToast(`Verificação concluída! ${data.updated_products} consoles atualizados.`, "success");
        if (data.triggered_alerts > 0) {
            showToast(`🔥 ${data.triggered_alerts} alerta(s) de preço disparados!`, "info");
        }

        document.getElementById("last-update-text").textContent = "Atualizado Agora";
        await loadProducts();

    } catch (err) {
        showToast("Erro ao executar verificação de preços.", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
            <span>Verificar Agora</span>
        `;
    }
}

// 8. Simulação de Oferta Relâmpago
async function simulatePromoDrop() {
    try {
        const resp = await fetch("/api/simulate-sale", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                product_id: selectedProductId,
                promo_price: 2999.00,
                store: "KaBuM! (Oferta Relâmpago)"
            })
        });
        const res = await resp.json();
        showToast("Promoção relâmpago de R$ 2.999,00 simulada com sucesso!", "success");
        await loadProducts();
        await loadLogs();
    } catch (err) {
        showToast("Erro ao simular promoção.", "error");
    }
}

// 9. Gerenciador de Alertas
async function loadAlerts() {
    try {
        const resp = await fetch("/api/alerts");
        const alerts = await resp.json();
        const list = document.getElementById("alerts-list");
        list.innerHTML = "";

        if (!alerts.length) {
            list.innerHTML = `<p class="text-muted" style="padding: 1rem 0;">Nenhum alerta cadastrado no momento. Cadastre seu primeiro alerta ao lado!</p>`;
            return;
        }

        alerts.forEach(a => {
            const item = document.createElement("div");
            item.className = "alert-item";
            item.innerHTML = `
                <div class="alert-item-info">
                    <strong>${a.product_name}</strong>
                    <span>Avisar abaixo de <strong class="text-success">R$ ${a.target_price.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong> ${a.alert_on_all_time_low ? '• Ou em Nova Mínima Histórica' : ''}</span>
                    <small style="display: block; color: #64748b; margin-top: 0.2rem;">Canal: ${a.channel.toUpperCase()} ${a.last_triggered_at ? '• Disparado em ' + formatDateBR(a.last_triggered_at) : ''}</small>
                </div>
                <button class="btn btn-sm btn-outline" style="color: #ef4444;" onclick="deleteAlert(${a.id})">Excluir</button>
            `;
            list.appendChild(item);
        });
    } catch (err) {
        console.error("Erro ao carregar alertas:", err);
    }
}

async function createAlert(e) {
    e.preventDefault();
    const product_id = document.getElementById("alert-product").value;
    const target_price = parseFloat(document.getElementById("alert-price").value);
    const alert_on_all_time_low = document.getElementById("alert-on-min").checked;
    const channel = document.getElementById("alert-channel").value;

    try {
        await fetch("/api/alerts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id, target_price, alert_on_all_time_low, channel })
        });
        showToast("Alerta de preço salvo com sucesso!", "success");
        document.getElementById("alert-price").value = "";
        await loadAlerts();
    } catch (err) {
        showToast("Erro ao cadastrar alerta.", "error");
    }
}

async function deleteAlert(id) {
    if (!confirm("Deseja remover este alerta?")) return;
    try {
        await fetch(`/api/alerts/${id}`, { method: "DELETE" });
        showToast("Alerta removido.", "info");
        await loadAlerts();
    } catch (err) {
        showToast("Erro ao remover alerta.", "error");
    }
}

// 10. Configurações e Testes de Notificação
async function loadSettings() {
    try {
        const resp = await fetch("/api/settings");
        const s = await resp.json();

        document.getElementById("setting-discord-url").value = s.discord_webhook_url || "";
        document.getElementById("setting-telegram-token").value = s.telegram_bot_token || "";
        document.getElementById("setting-telegram-chat").value = s.telegram_chat_id || "";

        document.getElementById("setting-email-host").value = s.email_smtp_host || "smtp.gmail.com";
        document.getElementById("setting-email-port").value = s.email_smtp_port || "587";
        document.getElementById("setting-email-user").value = s.email_user || "";
        document.getElementById("setting-email-pwd").value = s.email_password || "";
        document.getElementById("setting-email-recip").value = s.email_recipient || "";
    } catch (err) {
        console.error("Erro ao carregar configurações:", err);
    }
}

async function saveSettings(e) {
    e.preventDefault();
    const payload = {
        discord_webhook_url: document.getElementById("setting-discord-url").value.trim(),
        telegram_bot_token: document.getElementById("setting-telegram-token").value.trim(),
        telegram_chat_id: document.getElementById("setting-telegram-chat").value.trim(),
        email_smtp_host: document.getElementById("setting-email-host").value.trim(),
        email_smtp_port: document.getElementById("setting-email-port").value.trim(),
        email_user: document.getElementById("setting-email-user").value.trim(),
        email_password: document.getElementById("setting-email-pwd").value.trim(),
        email_recipient: document.getElementById("setting-email-recip").value.trim()
    };

    try {
        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        showToast("Configurações salvas com sucesso!", "success");
    } catch (err) {
        showToast("Erro ao salvar configurações.", "error");
    }
}

async function testNotification(channel) {
    showToast(`Enviando mensagem de teste para ${channel.toUpperCase()}...`, "info");
    try {
        const resp = await fetch("/api/test-notification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ channel })
        });
        const res = await resp.json();
        if (res.success) {
            showToast(`Mensagem de teste enviada para ${channel.toUpperCase()} com sucesso!`, "success");
        } else {
            showToast(`Falha no teste: ${res.error}`, "error");
        }
    } catch (err) {
        showToast(`Erro ao testar canal: ${err.message}`, "error");
    }
}

// 11. Histórico de Notificações Enviadas (Logs)
async function loadLogs() {
    try {
        const resp = await fetch("/api/logs");
        const logs = await resp.json();
        const tbody = document.getElementById("logs-table-body");
        tbody.innerHTML = "";

        if (!logs.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum disparo de notificação registrado ainda.</td></tr>`;
            return;
        }

        logs.forEach(l => {
            const tr = document.createElement("tr");
            const isSent = l.status === "sent";
            tr.innerHTML = `
                <td>${formatDateBR(l.created_at)}</td>
                <td><strong>${l.product_name || 'PS5'}</strong></td>
                <td>R$ ${l.price ? l.price.toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '--'}</td>
                <td><span class="channel-badge ${l.channel}-badge">${l.channel.toUpperCase()}</span></td>
                <td><span style="color: ${isSent ? '#10b981' : '#ef4444'}; font-weight: 700;">${isSent ? 'ENVIADO' : 'FALHA'}</span></td>
                <td><small style="color: #cbd5e1;">${l.message}</small></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Erro ao carregar logs:", err);
    }
}

// Utilitários
function formatDateBR(dateStr, shortMonth = false) {
    if (!dateStr) return "--";
    try {
        // Se for string YYYY-MM-DD, parsear diretamente os componentes numéricos
        // para evitar que new Date(dateStr) converta UTC meia-noite para 21h do dia anterior no Brasil (UTC-3)
        if (typeof dateStr === "string" && /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim())) {
            const parts = dateStr.trim().split("-");
            const y = parts[0];
            const m = parseInt(parts[1], 10);
            const d = parseInt(parts[2], 10);
            const monthsShort = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
            if (shortMonth) {
                return `${d}/${monthsShort[m - 1]}`;
            }
            return `${d.toString().padStart(2, '0')}/${m.toString().padStart(2, '0')}/${y}`;
        }
        
        // Se contiver horário (ex: YYYY-MM-DD HH:MM:SS)
        const d = new Date(dateStr.replace(" ", "T"));
        if (isNaN(d.getTime())) return dateStr;
        if (shortMonth) {
            const m = d.toLocaleDateString('pt-BR', { month: 'short' });
            return `${d.getDate()}/${m}`;
        }
        return d.toLocaleDateString('pt-BR');
    } catch {
        return dateStr;
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

function requestBrowserNotificationPermission() {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
}
