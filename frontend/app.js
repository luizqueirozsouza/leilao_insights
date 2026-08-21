const API_BASE = (window.LEILAO_CONFIG && window.LEILAO_CONFIG.API_BASE) || "/api";

const state = {
  uf: "",
  ufOptions: [],
  cities: [],
  neighborhoods: [],
  modalidades: [],
  tipos: [],
  sort: "price_asc",
  loading: true,
  searchTimer: null,
  session: null,
  authMode: "login",
  alertFilters: {
    uf: "",
    cities: [],
    neighborhoods: [],
    modalidades: [],
    tipos: [],
  },
  calculator: null,
  adminUsers: [],
  editingAdminUser: null,
};

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

const els = {
  statsTotal: document.querySelector("#stat-total"),
  statsCities: document.querySelector("#stat-cities"),
  statsAverage: document.querySelector("#stat-average"),
  statsMedian: document.querySelector("#stat-median"),
  lastUpdated: document.querySelector("#last-updated"),
  uf: document.querySelector("#filter-uf"),
  cityTrigger: document.querySelector("#city-trigger"),
  cityPanel: document.querySelector("#city-panel"),
  neighborhoodTrigger: document.querySelector("#neighborhood-trigger"),
  neighborhoodPanel: document.querySelector("#neighborhood-panel"),
  modalityTrigger: document.querySelector("#modality-trigger"),
  modalityPanel: document.querySelector("#modality-panel"),
  typeTrigger: document.querySelector("#type-trigger"),
  typePanel: document.querySelector("#type-panel"),
  sortButton: document.querySelector("#sort-button"),
  clearButton: document.querySelector("#clear-button"),
  searchButton: document.querySelector("#search-button"),
  toggleFilters: document.querySelector("#toggle-filters"),
  filterGrid: document.querySelector("#filter-grid"),
  properties: document.querySelector("#properties"),
  status: document.querySelector("#status"),
  template: document.querySelector("#property-template"),
  demoBanner: document.querySelector("#demo-banner"),
  demoText: document.querySelector("#demo-text"),
  demoCta: document.querySelector("#demo-cta"),
  accountBar: document.querySelector("#account-bar"),
  accountBtn: document.querySelector("#account-btn"),
  alertasBtn: document.querySelector("#alertas-btn"),
  authModal: document.querySelector("#auth-modal"),
  authClose: document.querySelector("#auth-close"),
  authTitle: document.querySelector("#auth-title"),
  authSub: document.querySelector("#auth-sub"),
  authForm: document.querySelector("#auth-form"),
  authEmail: document.querySelector("#auth-email"),
  authPassword: document.querySelector("#auth-password"),
  authError: document.querySelector("#auth-error"),
  authSubmit: document.querySelector("#auth-submit"),
  tabLogin: document.querySelector("#tab-login"),
  tabRegister: document.querySelector("#tab-register"),
  userModal: document.querySelector("#user-modal"),
  userClose: document.querySelector("#user-close"),
  userAvatar: document.querySelector("#user-avatar"),
  userName: document.querySelector("#user-name"),
  userEmail: document.querySelector("#user-email"),
  userSubscriptionStatus: document.querySelector("#user-subscription-status"),
  userSubscriptionStart: document.querySelector("#user-subscription-start"),
  userSubscriptionEnd: document.querySelector("#user-subscription-end"),
  userSubscriptionNote: document.querySelector("#user-subscription-note"),
  userAlertSummary: document.querySelector("#user-alert-summary"),
  userAlertsButton: document.querySelector("#user-alerts-button"),
  userLogout: document.querySelector("#user-logout"),
  adminEntryButton: document.querySelector("#admin-entry-button"),
  adminModal: document.querySelector("#admin-modal"),
  adminClose: document.querySelector("#admin-close"),
  adminRefresh: document.querySelector("#admin-refresh"),
  adminStatus: document.querySelector("#admin-status"),
  adminSummary: document.querySelector("#admin-summary"),
  adminUsersCount: document.querySelector("#admin-users-count"),
  adminUsersBody: document.querySelector("#admin-users-body"),
  adminAlertsCount: document.querySelector("#admin-alerts-count"),
  adminAlertsBody: document.querySelector("#admin-alerts-body"),
  adminUserEditModal: document.querySelector("#admin-user-edit-modal"),
  adminUserEditClose: document.querySelector("#admin-user-edit-close"),
  adminUserEditForm: document.querySelector("#admin-user-edit-form"),
  adminEditTitle: document.querySelector("#admin-edit-title"),
  adminEditEmailHint: document.querySelector("#admin-edit-email-hint"),
  adminEditName: document.querySelector("#admin-edit-name"),
  adminEditEmail: document.querySelector("#admin-edit-email"),
  adminEditActive: document.querySelector("#admin-edit-active"),
  adminEditSubscriptionActive: document.querySelector("#admin-edit-subscription-active"),
  adminEditSubscriptionStatus: document.querySelector("#admin-edit-subscription-status"),
  adminEditStart: document.querySelector("#admin-edit-start"),
  adminEditEnd: document.querySelector("#admin-edit-end"),
  adminEditError: document.querySelector("#admin-edit-error"),
  adminEditSubmit: document.querySelector("#admin-edit-submit"),
  alertsModal: document.querySelector("#alerts-modal"),
  alertsClose: document.querySelector("#alerts-close"),
  alertsStatus: document.querySelector("#alerts-status"),
  alertForm: document.querySelector("#alert-form"),
  alertUf: document.querySelector("#alert-uf"),
  alertCityTrigger: document.querySelector("#alert-city-trigger"),
  alertCityPanel: document.querySelector("#alert-city-panel"),
  alertNeighborhoodTrigger: document.querySelector("#alert-neighborhood-trigger"),
  alertNeighborhoodPanel: document.querySelector("#alert-neighborhood-panel"),
  alertModalityTrigger: document.querySelector("#alert-modality-trigger"),
  alertModalityPanel: document.querySelector("#alert-modality-panel"),
  alertTypeTrigger: document.querySelector("#alert-type-trigger"),
  alertTypePanel: document.querySelector("#alert-type-panel"),
  alertEmail: document.querySelector("#alert-email"),
  alertTelegram: document.querySelector("#alert-telegram"),
  alertTelegramId: document.querySelector("#alert-telegram-id"),
  alertSubmit: document.querySelector("#alert-submit"),
  alertsList: document.querySelector("#alerts-list"),
  detailModal: document.querySelector("#detail-modal"),
  detailClose: document.querySelector("#detail-close"),
  detailTitle: document.querySelector("#detail-title"),
  detailLoading: document.querySelector("#detail-loading"),
  detailBody: document.querySelector("#detail-body"),
  calculatorModal: document.querySelector("#calculator-modal"),
  calculatorClose: document.querySelector("#calculator-close"),
  calculatorSource: document.querySelector("#calculator-source"),
  calcValuation: document.querySelector("#calc-valuation"),
  calcAuction: document.querySelector("#calc-auction"),
  calcSale: document.querySelector("#calc-sale"),
  calcArea: document.querySelector("#calc-area"),
  calcSalePerArea: document.querySelector("#calc-sale-per-area"),
  calcFinancingEnabled: document.querySelector("#calc-financing-enabled"),
  financingFields: document.querySelector("#financing-fields"),
  financingSummary: document.querySelector("#financing-summary"),
  calcEntry: document.querySelector("#calc-entry"),
  calcInstallment: document.querySelector("#calc-installment"),
  calcMonths: document.querySelector("#calc-months"),
  calcDebt: document.querySelector("#calc-debt"),
  calcInstallmentsTotal: document.querySelector("#calc-installments-total"),
  calcTotalLabel: document.querySelector("#calc-total-label"),
  acquisitionCosts: document.querySelector("#acquisition-costs"),
  saleCosts: document.querySelector("#sale-costs"),
  calcTotal: document.querySelector("#calc-total"),
  calcSaleCosts: document.querySelector("#calc-sale-costs"),
  calcProfit: document.querySelector("#calc-profit"),
  calcMargin: document.querySelector("#calc-margin"),
  calcRoi: document.querySelector("#calc-roi"),
};

function setLoading(isLoading) {
  state.loading = isLoading;
  document.body.classList.toggle("loading", isLoading);
  els.uf.disabled = isLoading;
  els.cityTrigger.disabled = isLoading || !state.uf;
  els.neighborhoodTrigger.disabled = isLoading || !state.uf;
  els.modalityTrigger.disabled = isLoading;
  els.typeTrigger.disabled = isLoading;
  els.sortButton.disabled = isLoading;
  els.clearButton.disabled = isLoading;
  els.searchButton.disabled = isLoading;
  if (isLoading) {
    els.statsTotal.textContent = "...";
    els.statsCities.textContent = "...";
    els.statsAverage.textContent = "...";
    els.statsMedian.textContent = "...";
  }
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function qs(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => item && search.append(key, item));
    } else if (value) {
      search.set(key, value);
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

async function api(path, params, options = {}) {
  const method = options.method || "GET";
  const opts = {
    method,
    credentials: "include",
    cache: method === "GET" ? "no-store" : "default",
    headers: { "Content-Type": "application/json" },
  };
  if (method !== "GET") {
    opts.headers["X-CSRFToken"] = csrfToken();
  }
  if (options.body !== undefined) {
    opts.body = JSON.stringify(options.body);
  }
  const response = await fetch(`${API_BASE}${path}${qs(params)}`, opts);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const j = await response.json();
      if (j.error) detail = j.error;
    } catch (e) {}
    throw new Error(detail);
  }
  return response.json();
}

function setStatus(message) {
  els.status.hidden = !message;
  els.status.textContent = message || "";
}

function selectedParams() {
  return {
    uf: state.uf,
    city: state.cities,
    neighborhood: state.neighborhoods,
    modalidade: state.modalidades,
    tipo: state.tipos,
    sort: state.sort,
  };
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function closePanels() {
  document.querySelectorAll(".multi-panel.open").forEach((item) => item.classList.remove("open"));
}

function scheduleSearch() {
  window.clearTimeout(state.searchTimer);
  state.searchTimer = window.setTimeout(() => {
    search();
  }, 250);
}

function renderUfOptions() {
  els.uf.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "Todos";
  allOption.selected = state.uf === "";
  els.uf.appendChild(allOption);

  state.ufOptions.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.label} (${formatNumber(item.count)})`;
    option.selected = item.value === state.uf;
    els.uf.appendChild(option);
  });
}

function renderOptions(panel, groupName, options, selectedValues, onChange, config = {}) {
  panel.innerHTML = "";
  const { placeholder = "Digite para filtrar", multiple = true } = config;

  const searchWrap = document.createElement("div");
  searchWrap.className = "panel-search-wrap";

  const searchInput = document.createElement("input");
  searchInput.className = "panel-search";
  searchInput.type = "search";
  searchInput.placeholder = placeholder;
  searchInput.autocomplete = "off";
  searchWrap.appendChild(searchInput);
  panel.appendChild(searchWrap);

  const list = document.createElement("div");
  panel.appendChild(list);

  function draw(term = "") {
    list.innerHTML = "";
    const query = normalizeText(term);
    const filtered = options.filter((option) => (
      !query || normalizeText(option.label).includes(query) || normalizeText(option.value).includes(query)
    ));

    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.className = "status";
      empty.textContent = "Nenhuma opcao encontrada.";
      list.appendChild(empty);
      return;
    }

    filtered.forEach((option) => {
      const label = document.createElement("label");
      label.className = "option-row";

      const input = document.createElement("input");
      input.type = multiple ? "checkbox" : "radio";
      input.name = groupName;
      input.value = option.value;
      input.checked = selectedValues.includes(option.value);
      input.addEventListener("change", onChange);

      const text = document.createElement("span");
      text.textContent = option.label;

      const count = document.createElement("small");
      count.textContent = formatNumber(option.count);

      label.append(input, text, count);
      list.appendChild(label);
    });
  }

  searchInput.addEventListener("input", () => draw(searchInput.value));
  draw();
  panel._searchInput = searchInput;

  if (!options.length) {
    draw(searchInput.value);
  }
}

function readChecked(panel) {
  return Array.from(panel.querySelectorAll("input:checked")).map((input) => input.value);
}

function updateTrigger(trigger, values, emptyLabel, pluralLabel) {
  if (!values.length) {
    trigger.textContent = emptyLabel;
  } else if (values.length === 1) {
    trigger.textContent = values[0];
  } else {
    trigger.textContent = `${values.length} ${pluralLabel}`;
  }
}

function setupPanel(trigger, panel) {
  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    if (trigger.disabled) return;
    document.querySelectorAll(".multi-panel.open").forEach((item) => {
      if (item !== panel) item.classList.remove("open");
    });
    panel.classList.toggle("open");
    if (panel.classList.contains("open") && panel._searchInput) {
      panel._searchInput.focus();
      panel._searchInput.select();
    }
  });
  panel.addEventListener("click", (event) => event.stopPropagation());
}

async function loadFilters() {
  const data = await api("/filters", selectedParams());

  state.ufOptions = data.ufs;
  renderUfOptions();

  renderOptions(els.cityPanel, "city", data.cities, state.cities, async () => {
    state.cities = readChecked(els.cityPanel);
    state.neighborhoods = [];
    state.modalidades = [];
    state.tipos = [];
    updateTrigger(els.cityTrigger, state.cities, "Todas", "selecionadas");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar cidade" });

  renderOptions(els.neighborhoodPanel, "neighborhood", data.neighborhoods, state.neighborhoods, async () => {
    state.neighborhoods = readChecked(els.neighborhoodPanel);
    state.modalidades = [];
    state.tipos = [];
    updateTrigger(els.neighborhoodTrigger, state.neighborhoods, "Todos", "selecionados");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar bairro" });

  renderOptions(els.modalityPanel, "modalidade", data.modalidades, state.modalidades, async () => {
    state.modalidades = readChecked(els.modalityPanel);
    state.tipos = [];
    updateTrigger(els.modalityTrigger, state.modalidades, "Todas", "selecionadas");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar modalidade" });

  renderOptions(els.typePanel, "tipo", data.tipos, state.tipos, async () => {
    state.tipos = readChecked(els.typePanel);
    updateTrigger(els.typeTrigger, state.tipos, "Todos", "selecionados");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar tipo" });

  els.cityTrigger.disabled = state.loading || !state.uf;
  els.neighborhoodTrigger.disabled = state.loading || !state.uf;
  els.neighborhoodTrigger.disabled = state.loading || !state.cities.length;
  els.modalityTrigger.disabled = state.loading;
  updateTrigger(els.cityTrigger, state.cities, "Todas", "selecionadas");
  updateTrigger(els.neighborhoodTrigger, state.neighborhoods, "Todos", "selecionados");
  updateTrigger(els.modalityTrigger, state.modalidades, "Todas", "selecionadas");
  updateTrigger(els.typeTrigger, state.tipos, "Todos", "selecionados");
}

function renderProperties(properties) {
  els.properties.innerHTML = "";

  if (!properties.length) {
    setStatus("Nenhum imóvel encontrado para estes filtros.");
    return;
  }

  setStatus("");
  properties.forEach((property) => {
    const payload = property.payload || {};
    const node = els.template.content.cloneNode(true);
    const image = node.querySelector(".photo");
    const numero = property.numero_imovel || payload["Nº do imóvel"] || payload["NÂº do imÃ³vel"];

    image.src = `https://venda-imoveis.caixa.gov.br/fotos/F${numero}21.jpg`;
    image.alt = payload.Cidade || numero || "Imovel";
    image.addEventListener("error", () => {
      image.removeAttribute("src");
      image.style.display = "none";
    });

    node.querySelector(".uf-badge").textContent = property.uf || payload.UF || "";
    node.querySelector(".discount-badge").textContent = payload.Desconto ? `${payload.Desconto}%` : "";

    const tipo = property.tipo_imovel || payload.tipo_imovel;
    const typeBadge = node.querySelector(".type-badge");
    if (tipo) {
      typeBadge.textContent = tipo;
      typeBadge.hidden = false;
    }

    node.querySelector(".city").textContent = payload.Cidade || "-";
    node.querySelector(".modality").textContent = payload["Modalidade de venda"] || "-";
    node.querySelector(".neighborhood").textContent = payload.Bairro || "-";
    node.querySelector(".address").textContent = payload["Endereço"] || payload["EndereÃ§o"] || "";
    node.querySelector(".valuation").textContent = `R$ ${payload["Valor de avaliação"] || payload["Valor de avaliaÃ§Ã£o"] || "-"}`;
    node.querySelector(".price").textContent = `R$ ${payload["Preço"] || payload["PreÃ§o"] || "-"}`;
    node.querySelector(".description").textContent = payload["Descrição"] || payload["DescriÃ§Ã£o"] || "";

    const detailBtn = node.querySelector(".detail-button");
    detailBtn.dataset.numero = numero;
    detailBtn.addEventListener("click", () => openDetail(numero, payload));

    const simulateBtn = node.querySelector(".simulate-button");
    simulateBtn.addEventListener("click", () => openCalculator({ dados_enriquecidos: {} }, payload));

    const link = node.querySelector(".doc-link");
    link.href = payload["Link de acesso"] || "#";
    els.properties.appendChild(node);
  });
}

async function loadStatsAndProperties() {
  setStatus("Carregando imoveis...");
  try {
    const [stats, filteredStats, properties] = await Promise.all([
      api("/stats"),
      api("/stats/filtered", selectedParams()),
      api("/properties", { ...selectedParams(), limit: 48 }),
    ]);

    els.statsTotal.textContent = formatNumber(stats.total);
    els.statsCities.textContent = formatNumber(stats.cities);
    els.statsAverage.textContent = formatMoney(filteredStats.average);
    els.statsMedian.textContent = formatMoney(filteredStats.median);
    els.lastUpdated.textContent = stats.last_updated || "-";

    renderDemoBanner(stats.em_demo);

    renderProperties(properties);
  } catch (error) {
    setStatus("Nao foi possivel carregar os dados. Confira a URL da API.");
  }
}

async function search() {
  els.searchButton.disabled = true;
  try {
    // Revalidate the subscription before each refresh so admin changes take effect immediately.
    await loadSession();
    await loadFilters();
    await loadStatsAndProperties();
  } finally {
    els.searchButton.disabled = state.loading;
  }
}

// ---------- Sessao / auth ----------

function isAssinante() {
  return !!(state.session && state.session.autenticado && state.session.assinatura && state.session.assinatura.ativa);
}

function isAuthenticated() {
  return !!(state.session && state.session.autenticado);
}

function renderDemoBanner(isDemo) {
  const authenticated = isAuthenticated();
  els.demoBanner.hidden = !isDemo || isAssinante();
  els.demoCta.hidden = authenticated;
  els.demoText.innerHTML = authenticated
    ? "Voce esta vendo uma amostra de imoveis. <strong>Assine</strong> para acessar o acervo completo e receber alertas de novos imoveis."
    : "Voce esta vendo uma amostra de imoveis. <strong>Crie sua conta e assine</strong> para acessar o acervo completo e receber alertas de novos imoveis.";
}

function renderAuthOptions() {
  els.tabRegister.hidden = isAuthenticated();
  if (isAuthenticated() && state.authMode === "register") {
    setAuthMode("login");
  }
}

function renderAccount() {
  renderAuthOptions();
  renderDemoBanner(false);
  if (!state.session || !state.session.autenticado) {
    els.accountBtn.textContent = "Entrar";
    els.accountBtn.onclick = () => openAuth("login");
    els.alertasBtn.hidden = true;
    return;
  }
  els.accountBtn.textContent = state.session.nome || "Minha conta";
  els.accountBtn.onclick = () => openUserPanel();
  els.alertasBtn.hidden = !isAssinante();
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString("pt-BR");
}

function renderUserPanel() {
  const session = state.session;
  if (!session || !session.autenticado) return;
  const name = session.nome || "Usuário";
  const subscription = session.assinatura;
  const preferences = session.preferencias || [];
  els.userName.textContent = name;
  els.userEmail.textContent = session.email || "-";
  els.userAvatar.textContent = name.trim().charAt(0).toUpperCase() || "U";
  els.userSubscriptionStatus.textContent = subscription && subscription.ativa ? "Ativa" : "Inativa";
  els.userSubscriptionStatus.className = `subscription-badge ${subscription && subscription.ativa ? "active" : "inactive"}`;
  els.userSubscriptionStart.textContent = formatDate(subscription && subscription.data_inicio);
  els.userSubscriptionEnd.textContent = formatDate(subscription && subscription.data_fim);
  els.userSubscriptionNote.textContent = subscription && subscription.ativa
    ? "Sua conta tem acesso ao acervo completo e aos alertas."
    : "A assinatura ativa libera o acervo completo e o recebimento de alertas.";
  els.userAlertSummary.textContent = preferences.length === 1
    ? "Você possui 1 alerta configurado."
    : `Você possui ${preferences.length} alertas configurados.`;
  els.userAlertsButton.disabled = !isAssinante();
  els.userAlertsButton.textContent = isAssinante() ? "Gerenciar alertas" : "Exige assinatura";
  els.adminEntryButton.hidden = !session.administrador;
}

function openUserPanel() {
  renderUserPanel();
  els.userModal.hidden = false;
}

function showAdminStatus(message, isError = false) {
  els.adminStatus.hidden = !message;
  els.adminStatus.textContent = message || "";
  els.adminStatus.className = `admin-status ${isError ? "error" : ""}`;
}

function renderAdminOverview(data) {
  const summary = data.resumo || {};
  els.adminSummary.innerHTML = [
    ["Usuários", summary.usuarios || 0],
    ["Assinaturas ativas", summary.assinaturas_ativas || 0],
    ["Alertas", summary.alertas || 0],
  ].map(([label, value]) => `<div><span>${label}</span><strong>${formatNumber(value)}</strong></div>`).join("");

  const users = data.usuarios || [];
  state.adminUsers = users;
  els.adminUsersCount.textContent = `${formatNumber(users.length)} registrados`;
  els.adminUsersBody.innerHTML = users.length ? users.map((user) => {
    const subscription = user.assinatura;
    const status = subscription && subscription.ativa ? "Ativa" : "Inativa";
    return `<tr>
      <td><strong>${escapeHtml(user.nome || "Usuário")}</strong><small>${escapeHtml(user.email || "-")}</small></td>
      <td><span class="table-badge ${subscription && subscription.ativa ? "active" : "inactive"}">${status}</span>${subscription && subscription.data_fim ? `<small>até ${formatDate(subscription.data_fim)}</small>` : ""}</td>
      <td>${formatNumber(user.alertas || 0)}</td>
      <td>${formatDateTime(user.criado_em)}</td>
      <td><button class="table-action-button" type="button" data-admin-edit-user="${user.id}">Editar</button></td>
    </tr>`;
  }).join("") : '<tr><td colspan="5" class="table-empty">Nenhum usuário encontrado.</td></tr>';

  const alerts = data.alertas || [];
  els.adminAlertsCount.textContent = `${formatNumber(alerts.length)} cadastrados`;
  els.adminAlertsBody.innerHTML = alerts.length ? alerts.map((alert) => {
    const filters = [
      alert.uf ? `UF: ${alert.uf}` : "Todas as UFs",
      alert.cidades && alert.cidades.length ? `Cidades: ${alert.cidades.join(", ")}` : null,
      alert.bairros && alert.bairros.length ? `Bairros: ${alert.bairros.join(", ")}` : null,
      alert.modalidades && alert.modalidades.length ? `Modalidades: ${alert.modalidades.join(", ")}` : null,
      alert.tipos && alert.tipos.length ? `Tipos: ${alert.tipos.join(", ")}` : null,
    ].filter(Boolean);
    const channels = [alert.canal_email ? "E-mail" : null, alert.canal_telegram ? "Telegram" : null].filter(Boolean);
    return `<tr>
      <td><strong>${escapeHtml(alert.nome || "Usuário")}</strong><small>${escapeHtml(alert.usuario || "-")}</small></td>
      <td><small>${escapeHtml(filters.join(" · "))}</small></td>
      <td>${escapeHtml(channels.join(" / ") || "Nenhum")}</td>
      <td>${formatDateTime(alert.criada_em)}</td>
    </tr>`;
  }).join("") : '<tr><td colspan="4" class="table-empty">Nenhum alerta cadastrado.</td></tr>';
}

function openAdminUserEdit(userId) {
  const user = state.adminUsers.find((item) => item.id === Number(userId));
  if (!user) return;
  state.editingAdminUser = user;
  const subscription = user.assinatura || {};
  els.adminEditTitle.textContent = `Editar ${user.nome || "usuário"}`;
  els.adminEditEmailHint.textContent = user.email || "";
  els.adminEditName.value = user.nome || "";
  els.adminEditEmail.value = user.email || "";
  els.adminEditActive.checked = user.ativo !== false;
  els.adminEditSubscriptionActive.checked = !!subscription.ativa;
  els.adminEditSubscriptionStatus.textContent = subscription.ativa ? "Ativa" : "Inativa";
  els.adminEditStart.value = subscription.data_inicio || "";
  els.adminEditEnd.value = subscription.data_fim || "";
  els.adminEditError.hidden = true;
  els.adminUserEditModal.hidden = false;
}

function closeAdminUserEdit() {
  els.adminUserEditModal.hidden = true;
  state.editingAdminUser = null;
}

async function handleAdminUserEdit(event) {
  event.preventDefault();
  const user = state.editingAdminUser;
  if (!user) return;
  els.adminEditError.hidden = true;
  els.adminEditSubmit.disabled = true;
  try {
    await api(`/admin/users/${user.id}`, {}, {
      method: "PUT",
      body: {
        nome: els.adminEditName.value.trim(),
        email: els.adminEditEmail.value.trim(),
        ativo: els.adminEditActive.checked,
      },
    });
    await api(`/admin/users/${user.id}/subscription`, {}, {
      method: "PUT",
      body: {
        ativa: els.adminEditSubscriptionActive.checked,
        data_inicio: els.adminEditStart.value || null,
        data_fim: els.adminEditEnd.value || null,
      },
    });
    closeAdminUserEdit();
    await openAdminPanel();
  } catch (error) {
    els.adminEditError.textContent = error.message || "Não foi possível salvar as alterações.";
    els.adminEditError.hidden = false;
  } finally {
    els.adminEditSubmit.disabled = false;
  }
}

async function openAdminPanel() {
  if (!state.session || !state.session.administrador) return;
  els.userModal.hidden = true;
  els.adminModal.hidden = false;
  showAdminStatus("Carregando dados administrativos...");
  els.adminRefresh.disabled = true;
  try {
    const data = await api("/admin/overview");
    renderAdminOverview(data);
    showAdminStatus("");
  } catch (error) {
    showAdminStatus(error.message || "Não foi possível carregar o painel administrativo.", true);
  } finally {
    els.adminRefresh.disabled = false;
  }
}

async function loadSession() {
  try {
    state.session = await api("/me");
  } catch (e) {
    state.session = null;
  }
  renderAccount();
}

function openAuth(mode) {
  state.authMode = mode;
  setAuthMode(mode);
  els.authError.hidden = true;
  els.authModal.hidden = false;
}

function setAuthMode(mode) {
  const isLogin = mode === "login";
  els.authTitle.textContent = isLogin ? "Entrar" : "Criar conta";
  els.authSub.textContent = isLogin
    ? "Acesse sua conta para ver todos os imoveis."
    : "Crie sua conta para comecar a usar o painel.";
  els.authSubmit.textContent = isLogin ? "Entrar" : "Criar conta";
  els.tabLogin.classList.toggle("active", isLogin);
  els.tabRegister.classList.toggle("active", !isLogin);
  els.authPassword.autocomplete = isLogin ? "current-password" : "new-password";
  els.authEmail.type = isLogin ? "text" : "email";
  els.authEmail.autocomplete = isLogin ? "username" : "email";
  els.authEmail.placeholder = isLogin ? "voce@email.com ou admin" : "voce@email.com";
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = els.authEmail.value.trim();
  const senha = els.authPassword.value;
  els.authError.hidden = true;
  try {
    if (state.authMode === "login") {
      await api("/login", {}, { method: "POST", body: { email, senha } });
    } else {
      await api("/registro", {}, { method: "POST", body: { email, senha } });
    }
    els.authModal.hidden = true;
    els.authForm.reset();
    await loadSession();
    await loadFilters();
    await search();
  } catch (error) {
    els.authError.textContent = error.message;
    els.authError.hidden = false;
  }
}

async function logout() {
  try {
    await api("/logout", {}, { method: "POST" });
  } catch (e) {}
  state.session = null;
  renderAccount();
  await loadFilters();
  await search();
}

// ---------- Alertas ----------

function parseList(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function fillAlertUfOptions() {
  els.alertUf.innerHTML = '<option value="">Todas</option>';
  state.ufOptions.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.value;
    opt.textContent = item.label;
    els.alertUf.appendChild(opt);
  });
}

function alertFilterParams() {
  const filters = state.alertFilters;
  return {
    uf: filters.uf,
    city: filters.cities,
    neighborhood: filters.neighborhoods,
    modalidade: filters.modalidades,
    tipo: filters.tipos,
  };
}

function renderAlertUfOptions() {
  els.alertUf.innerHTML = '<option value="">Todas</option>';
  state.ufOptions.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.label} (${formatNumber(item.count)})`;
    option.selected = item.value === state.alertFilters.uf;
    els.alertUf.appendChild(option);
  });
}

async function loadAlertFilters() {
  const data = await api("/filters", alertFilterParams());
  renderAlertUfOptions();

  renderOptions(els.alertCityPanel, "alert-city", data.cities, state.alertFilters.cities, async () => {
    state.alertFilters.cities = readChecked(els.alertCityPanel);
    state.alertFilters.neighborhoods = [];
    state.alertFilters.modalidades = [];
    state.alertFilters.tipos = [];
    await loadAlertFilters();
  }, { placeholder: "Digite para buscar cidade" });

  renderOptions(els.alertNeighborhoodPanel, "alert-neighborhood", data.neighborhoods, state.alertFilters.neighborhoods, async () => {
    state.alertFilters.neighborhoods = readChecked(els.alertNeighborhoodPanel);
    state.alertFilters.modalidades = [];
    state.alertFilters.tipos = [];
    await loadAlertFilters();
  }, { placeholder: "Digite para buscar bairro" });

  renderOptions(els.alertModalityPanel, "alert-modalidade", data.modalidades, state.alertFilters.modalidades, async () => {
    state.alertFilters.modalidades = readChecked(els.alertModalityPanel);
    await loadAlertFilters();
  }, { placeholder: "Digite para buscar modalidade" });

  renderOptions(els.alertTypePanel, "alert-tipo", data.tipos, state.alertFilters.tipos, async () => {
    state.alertFilters.tipos = readChecked(els.alertTypePanel);
    await loadAlertFilters();
  }, { placeholder: "Digite para buscar tipo de imóvel" });

  els.alertCityTrigger.disabled = !state.alertFilters.uf;
  els.alertNeighborhoodTrigger.disabled = !state.alertFilters.cities.length;
  els.alertModalityTrigger.disabled = false;
  els.alertTypeTrigger.disabled = false;
  updateTrigger(els.alertCityTrigger, state.alertFilters.cities, "Todas", "selecionadas");
  updateTrigger(els.alertNeighborhoodTrigger, state.alertFilters.neighborhoods, "Todos", "selecionados");
  updateTrigger(els.alertModalityTrigger, state.alertFilters.modalidades, "Todas", "selecionadas");
  updateTrigger(els.alertTypeTrigger, state.alertFilters.tipos, "Todos", "selecionados");
}

function renderAlertas(list) {
  els.alertsList.innerHTML = "";
  if (!list.length) {
    els.alertsList.innerHTML = '<p class="modal-sub">Nenhum alerta configurado.</p>';
    return;
  }
  list.forEach((pref) => {
    const row = document.createElement("div");
    row.className = "alert-row";
    const chips = [
      pref.uf ? `UF: ${pref.uf}` : "UF: todas",
      pref.cidades.length ? `Cidades: ${pref.cidades.join(", ")}` : null,
      pref.bairros.length ? `Bairros: ${pref.bairros.join(", ")}` : null,
      pref.modalidades.length ? `Modalidades: ${pref.modalidades.join(", ")}` : null,
    ].filter(Boolean);
    const canais = [];
    if (pref.canal_email) canais.push("e-mail");
    if (pref.canal_telegram) canais.push("Telegram");
    row.innerHTML = `<div class="alert-row-info">${chips.join(" · ")}</div><div class="alert-row-can">${canais.join(" / ") || "sem canal"}</div>`;
    const del = document.createElement("button");
    del.type = "button";
    del.className = "alert-delete";
    del.textContent = "Remover";
    del.addEventListener("click", async () => {
      try {
        await api(`/preferencias/${pref.id}`, {}, { method: "DELETE" });
        await openAlertas();
      } catch (e) {
        showAlertsStatus(e.message, true);
      }
    });
    row.appendChild(del);
    els.alertsList.appendChild(row);
  });
}

function showAlertsStatus(msg, isError) {
  els.alertsStatus.hidden = false;
  els.alertsStatus.textContent = msg;
  els.alertsStatus.className = "alerts-status " + (isError ? "error" : "ok");
}

async function openAlertas() {
  els.alertsStatus.hidden = true;
  els.alertForm.reset();
  els.alertEmail.checked = true;
  els.alertTelegram.checked = false;
  els.alertTelegramId.value = "";
  state.alertFilters = { uf: "", cities: [], neighborhoods: [], modalidades: [], tipos: [] };
  fillAlertUfOptions();
  try {
    await loadAlertFilters();
    const data = await api("/me");
    renderAlertas(data.preferencias || []);
    els.alertsModal.hidden = false;
  } catch (e) {
    showAlertsStatus("Nao foi possivel carregar seus alertas.", true);
  }
}

async function handleAlertSubmit(event) {
  event.preventDefault();
  const body = {
    uf: state.alertFilters.uf,
    cidades: state.alertFilters.cities,
    bairros: state.alertFilters.neighborhoods,
    modalidades: state.alertFilters.modalidades,
    tipos: state.alertFilters.tipos,
    canal_email: els.alertEmail.checked,
    canal_telegram: els.alertTelegram.checked,
    contato_telegram: els.alertTelegramId.value.trim(),
  };
  try {
    await api("/preferencias", {}, { method: "POST", body });
    showAlertsStatus("Alerta salvo com sucesso.", false);
    els.alertForm.reset();
    els.alertEmail.checked = true;
    state.alertFilters = { uf: "", cities: [], neighborhoods: [], modalidades: [], tipos: [] };
    await loadAlertFilters();
    const data = await api("/me");
    renderAlertas(data.preferencias || []);
  } catch (e) {
    showAlertsStatus(e.message, true);
  }
}

// ---------- Detalhe enriquecido ----------

const calculatorCostDefinitions = [
  { key: "itbi", label: "ITBI", group: "acquisition" },
  { key: "registry", label: "Cartório e registro", group: "acquisition" },
  { key: "reform", label: "Reforma", group: "acquisition" },
  { key: "acquisitionOther", label: "Outros custos de aquisição", group: "acquisition" },
  { key: "brokerage", label: "Corretagem", group: "sale" },
  { key: "saleTaxes", label: "Impostos da venda", group: "sale" },
  { key: "saleOther", label: "Outros custos da venda", group: "sale" },
];

function parseMoneyValue(value) {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  const text = String(value || "").replace(/[^\d,.-]/g, "").trim();
  if (!text) return 0;
  const normalized = text.includes(",")
    ? text.replace(/\./g, "").replace(",", ".")
    : text;
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

function firstPayloadValue(payload, keys) {
  return keys.map((key) => payload[key]).find((value) => value !== undefined && value !== null && String(value).trim() !== "") || "";
}

function renderCalculatorCostRows() {
  const baseOptions = [
    ["auction", "Valor de arrematação"],
    ["valuation", "Valor de avaliação"],
    ["sale", "Valor estimado de venda"],
  ];

  [els.acquisitionCosts, els.saleCosts].forEach((container) => {
    container.innerHTML = "";
  });

  calculatorCostDefinitions.forEach((definition) => {
    const row = document.createElement("div");
    row.className = "cost-row";
    row.dataset.costKey = definition.key;
    row.innerHTML = `
      <div class="cost-label"><strong>${definition.label}</strong><span class="cost-calculated" data-cost-result>R$ 0,00</span></div>
      <input class="cost-value" data-cost-value type="number" min="0" step="0.01" value="0" aria-label="Valor de ${definition.label}" />
      <select class="cost-mode" data-cost-mode aria-label="Modo de ${definition.label}">
        <option value="fixed">Fixo (R$)</option>
        <option value="percent">Percentual (%)</option>
      </select>
      <select class="cost-base" data-cost-base aria-label="Base de ${definition.label}">
        ${baseOptions.map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
      </select>`;
    const mode = row.querySelector("[data-cost-mode]");
    const base = row.querySelector("[data-cost-base]");
    const value = row.querySelector("[data-cost-value]");
    const update = () => {
      base.hidden = mode.value !== "percent";
      value.max = mode.value === "percent" ? "100" : "";
      recalculateCalculator();
    };
    mode.addEventListener("change", update);
    base.addEventListener("change", recalculateCalculator);
    value.addEventListener("input", recalculateCalculator);
    (definition.group === "acquisition" ? els.acquisitionCosts : els.saleCosts).appendChild(row);
    update();
  });
}

function calculatorBaseValue(base) {
  const calc = state.calculator || {};
  if (base === "auction") return calc.auction || 0;
  if (base === "valuation") return calc.valuation || 0;
  if (base === "sale") return calc.sale || 0;
  return 0;
}

function costRowAmount(row) {
  const valueInput = row.querySelector("[data-cost-value]");
  const mode = row.querySelector("[data-cost-mode]").value;
  const base = row.querySelector("[data-cost-base]").value;
  const value = Math.max(0, parseMoneyValue(valueInput.value));
  valueInput.value = value;
  return mode === "percent" ? calculatorBaseValue(base) * value / 100 : value;
}

function recalculateCalculator() {
  if (!state.calculator) return;
  state.calculator.valuation = Math.max(0, parseMoneyValue(els.calcValuation.value));
  state.calculator.auction = Math.max(0, parseMoneyValue(els.calcAuction.value));
  state.calculator.sale = Math.max(0, parseMoneyValue(els.calcSale.value));
  state.calculator.area = Math.max(0, parseMoneyValue(els.calcArea.value));
  state.calculator.financing = {
    enabled: els.calcFinancingEnabled.checked,
    entry: Math.max(0, parseMoneyValue(els.calcEntry.value)),
    installment: Math.max(0, parseMoneyValue(els.calcInstallment.value)),
    months: Math.floor(Math.max(0, parseMoneyValue(els.calcMonths.value))),
    debt: Math.max(0, parseMoneyValue(els.calcDebt.value)),
  };

  const acquisition = Array.from(els.acquisitionCosts.querySelectorAll(".cost-row"));
  const sale = Array.from(els.saleCosts.querySelectorAll(".cost-row"));
  const acquisitionTotal = acquisition.reduce((total, row) => {
    const amount = costRowAmount(row);
    row.querySelector("[data-cost-result]").textContent = formatMoney(amount);
    return total + amount;
  }, 0);
  const saleTotal = sale.reduce((total, row) => {
    const amount = costRowAmount(row);
    row.querySelector("[data-cost-result]").textContent = formatMoney(amount);
    return total + amount;
  }, 0);
  const financing = state.calculator.financing;
  const installmentsPaid = financing.enabled ? financing.installment * financing.months : 0;
  const investment = financing.enabled
    ? financing.entry + acquisitionTotal + installmentsPaid
    : state.calculator.auction + acquisitionTotal;
  const profit = state.calculator.sale - investment - saleTotal - (financing.enabled ? financing.debt : 0);
  const margin = state.calculator.sale ? (profit / state.calculator.sale) * 100 : null;
  const roi = investment ? (profit / investment) * 100 : null;
  const salePerArea = state.calculator.sale && state.calculator.area
    ? state.calculator.sale / state.calculator.area
    : null;

  els.calcTotal.textContent = formatMoney(investment);
  els.calcSaleCosts.textContent = formatMoney(saleTotal);
  els.calcProfit.textContent = formatMoney(profit);
  els.calcProfit.classList.toggle("negative", profit < 0);
  els.calcMargin.textContent = margin === null ? "-" : `${margin.toFixed(2).replace(".", ",")}%`;
  els.calcRoi.textContent = roi === null ? "-" : `${roi.toFixed(2).replace(".", ",")}%`;
  els.calcSalePerArea.textContent = salePerArea === null ? "-" : `${formatMoney(salePerArea)} / m²`;
  els.calcTotalLabel.textContent = financing.enabled ? "Capital investido" : "Investimento total";
  els.calcInstallmentsTotal.textContent = formatMoney(installmentsPaid);
}

function openCalculator(data, payload) {
  const enriched = data.dados_enriquecidos || {};
  const valuation = firstPayloadValue(payload, ["Valor de avaliacao", "Valor de avalia\u00e7\u00e3o"]);
  const auction = firstPayloadValue(payload, ["Preco", "Pre\u00e7o"]);
  const area = firstPayloadValue(enriched, ["area_privativa", "area_terreno", "area"]);
  state.calculator = {
    valuation: parseMoneyValue(valuation),
    auction: parseMoneyValue(auction),
    sale: 0,
    area: parseMoneyValue(area),
    financing: { enabled: false, entry: 0, installment: 0, months: 0, debt: 0 },
  };
  els.calculatorSource.textContent = `${payload.Cidade || "Imóvel"}${payload.Bairro ? ` · ${payload.Bairro}` : ""}`;
  els.calcValuation.value = state.calculator.valuation || "";
  els.calcAuction.value = state.calculator.auction || "";
  els.calcSale.value = "";
  els.calcArea.value = state.calculator.area || "";
  els.calcFinancingEnabled.checked = false;
  els.calcEntry.value = "";
  els.calcInstallment.value = "";
  els.calcMonths.value = "";
  els.calcDebt.value = "";
  els.financingFields.hidden = true;
  els.financingSummary.hidden = true;
  renderCalculatorCostRows();
  els.calculatorModal.hidden = false;
  recalculateCalculator();
  els.calcSale.focus();
}

function closeCalculator() {
  els.calculatorModal.hidden = true;
  state.calculator = null;
}

function openDetail(numero, payload) {
  els.detailModal.hidden = false;
  els.detailLoading.hidden = false;
  els.detailBody.hidden = true;
  els.detailBody.innerHTML = "";
  els.detailTitle.textContent = `Detalhes — ${numero}`;
  api(`/property/${numero}`)
    .then((data) => {
      els.detailLoading.hidden = true;
      els.detailBody.hidden = false;
      els.detailBody.innerHTML = renderDetail(data, payload);
    })
    .catch((error) => {
      els.detailLoading.hidden = true;
      els.detailBody.hidden = false;
      els.detailBody.innerHTML = `<p class="modal-sub">Não foi possível carregar os detalhes enriquecidos: ${error.message}</p>`;
    });
}

function renderDetail(data, payload) {
  const d = data.dados_enriquecidos || {};
  const rows = [
    ["Cidade", payload.Cidade],
    ["Bairro", payload.Bairro],
    ["Endereço", payload["Endereço"] || payload["EndereÃ§o"]],
    ["Tipo de imóvel", d.tipo_imovel || payload.tipo_imovel],
    ["Quartos", d.quartos],
    ["Garagem", d.garagem],
    ["Área privativa", d.area_privativa],
    ["Área do terreno", d.area_terreno],
    ["Matrícula", d.matricula],
    ["Comarca", d.comarca],
    ["Ofício", d.oficio],
    ["Inscrição imobiliária", d.inscricao_imobiliaria],
    ["Valor de avaliação", payload["Valor de avaliação"] || payload["Valor de avaliaÃ§Ã£o"]],
    ["Preço", payload["Preço"] || payload["PreÃ§o"]],
    ["Modalidade", payload["Modalidade de venda"]],
  ].filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== "");

  let html = '<button class="calculator-open-button" type="button" data-open-calculator>Simular aquisição</button>';
  html += '<div class="detail-grid">';
  rows.forEach(([label, value]) => {
    html += `<div class="detail-item"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`;
  });
  html += "</div>";

  if (d.formas_pagamento) {
    html += `<div class="detail-section"><h3>Formas de pagamento</h3><p>${escapeHtml(d.formas_pagamento)}</p></div>`;
  }
  if (d.regras_despesas) {
    html += `<div class="detail-section"><h3>Regras do certame (despesas)</h3><p>${escapeHtml(d.regras_despesas)}</p></div>`;
  }

  if (payload["Link de acesso"]) {
    html += `<div class="detail-section"><a class="doc-link inline" href="${escapeHtml(payload["Link de acesso"])}" target="_blank" rel="noopener noreferrer">Ver documentacao na Caixa</a></div>`;
  }

  window.setTimeout(() => {
    const button = els.detailBody.querySelector("[data-open-calculator]");
    if (button) button.addEventListener("click", () => openCalculator(data, payload));
  }, 0);

  return html;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function bindEvents() {
  setupPanel(els.cityTrigger, els.cityPanel);
  setupPanel(els.neighborhoodTrigger, els.neighborhoodPanel);
  setupPanel(els.modalityTrigger, els.modalityPanel);
  setupPanel(els.typeTrigger, els.typePanel);
  setupPanel(els.alertCityTrigger, els.alertCityPanel);
  setupPanel(els.alertNeighborhoodTrigger, els.alertNeighborhoodPanel);
  setupPanel(els.alertModalityTrigger, els.alertModalityPanel);
  setupPanel(els.alertTypeTrigger, els.alertTypePanel);

  document.addEventListener("click", closePanels);

  els.uf.addEventListener("change", async () => {
    state.uf = els.uf.value;
    state.cities = [];
    state.neighborhoods = [];
    state.modalidades = [];
    state.tipos = [];
    await loadFilters();
    scheduleSearch();
  });

  els.sortButton.addEventListener("click", () => {
    state.sort = state.sort === "price_asc" ? "price_desc" : "price_asc";
    els.sortButton.textContent = state.sort === "price_asc" ? "Menor preco" : "Maior preco";
    scheduleSearch();
  });

  els.clearButton.addEventListener("click", async () => {
    state.uf = "";
    state.cities = [];
    state.neighborhoods = [];
    state.modalidades = [];
    state.tipos = [];
    state.sort = "price_asc";
    await loadFilters();
    await search();
  });

  els.searchButton.addEventListener("click", search);
  window.addEventListener("focus", () => {
    if (!state.loading) search();
  });
  els.toggleFilters.addEventListener("click", () => {
    els.filterGrid.hidden = !els.filterGrid.hidden;
  });

  // Auth
  els.accountBtn.addEventListener("click", () => {});
  els.tabLogin.addEventListener("click", () => setAuthMode("login"));
  els.tabRegister.addEventListener("click", () => setAuthMode("register"));
  els.authClose.addEventListener("click", () => (els.authModal.hidden = true));
  els.authModal.addEventListener("click", (e) => { if (e.target === els.authModal) els.authModal.hidden = true; });
  els.authForm.addEventListener("submit", handleAuthSubmit);
  els.demoCta.addEventListener("click", () => openAuth("register"));
  els.userClose.addEventListener("click", () => (els.userModal.hidden = true));
  els.userModal.addEventListener("click", (e) => { if (e.target === els.userModal) els.userModal.hidden = true; });
  els.userLogout.addEventListener("click", async () => {
    els.userModal.hidden = true;
    await logout();
  });
  els.userAlertsButton.addEventListener("click", async () => {
    els.userModal.hidden = true;
    await openAlertas();
  });
  els.adminEntryButton.addEventListener("click", openAdminPanel);
  els.adminClose.addEventListener("click", () => (els.adminModal.hidden = true));
  els.adminModal.addEventListener("click", (e) => { if (e.target === els.adminModal) els.adminModal.hidden = true; });
  els.adminRefresh.addEventListener("click", openAdminPanel);
  els.adminUsersBody.addEventListener("click", (event) => {
    const button = event.target.closest("[data-admin-edit-user]");
    if (button) openAdminUserEdit(button.dataset.adminEditUser);
  });
  els.adminUserEditClose.addEventListener("click", closeAdminUserEdit);
  els.adminUserEditModal.addEventListener("click", (e) => { if (e.target === els.adminUserEditModal) closeAdminUserEdit(); });
  els.adminUserEditForm.addEventListener("submit", handleAdminUserEdit);

  // Alertas
  els.alertasBtn.addEventListener("click", openAlertas);
  els.alertsClose.addEventListener("click", () => (els.alertsModal.hidden = true));
  els.alertsModal.addEventListener("click", (e) => { if (e.target === els.alertsModal) els.alertsModal.hidden = true; });
  els.alertForm.addEventListener("submit", handleAlertSubmit);
  els.alertUf.addEventListener("change", async () => {
    state.alertFilters.uf = els.alertUf.value;
    state.alertFilters.cities = [];
    state.alertFilters.neighborhoods = [];
    state.alertFilters.modalidades = [];
    state.alertFilters.tipos = [];
    await loadAlertFilters();
  });

  // Detalhe
  els.detailClose.addEventListener("click", () => (els.detailModal.hidden = true));
  els.detailModal.addEventListener("click", (e) => { if (e.target === els.detailModal) els.detailModal.hidden = true; });

  // Calculadora publica
  [els.calcValuation, els.calcAuction, els.calcSale, els.calcArea].forEach((input) => {
    input.addEventListener("input", recalculateCalculator);
  });
  [els.calcEntry, els.calcInstallment, els.calcMonths, els.calcDebt].forEach((input) => {
    input.addEventListener("input", recalculateCalculator);
  });
  els.calcFinancingEnabled.addEventListener("change", () => {
    const enabled = els.calcFinancingEnabled.checked;
    els.financingFields.hidden = !enabled;
    els.financingSummary.hidden = !enabled;
    recalculateCalculator();
  });
  els.calculatorClose.addEventListener("click", closeCalculator);
  els.calculatorModal.addEventListener("click", (e) => {
    if (e.target === els.calculatorModal) closeCalculator();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!els.calculatorModal.hidden) closeCalculator();
    else if (!els.detailModal.hidden) els.detailModal.hidden = true;
    else if (!els.alertsModal.hidden) els.alertsModal.hidden = true;
    else if (!els.userModal.hidden) els.userModal.hidden = true;
    else if (!els.adminUserEditModal.hidden) closeAdminUserEdit();
    else if (!els.adminModal.hidden) els.adminModal.hidden = true;
    else if (!els.authModal.hidden) els.authModal.hidden = true;
  });
}

async function init() {
  setLoading(true);
  setStatus("Carregando filtros e estatisticas...");
  bindEvents();
  await loadSession();
  try {
    await loadFilters();
    await search();
  } finally {
    setLoading(false);
  }
}

init();
