const API_BASE = (window.LEILAO_CONFIG && window.LEILAO_CONFIG.API_BASE) || "/api";

const state = {
  uf: "",
  ufOptions: [],
  cities: [],
  neighborhoods: [],
  modalidades: [],
  sort: "price_asc",
  loading: true,
  searchTimer: null
};

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
  sortButton: document.querySelector("#sort-button"),
  clearButton: document.querySelector("#clear-button"),
  searchButton: document.querySelector("#search-button"),
  toggleFilters: document.querySelector("#toggle-filters"),
  filterGrid: document.querySelector("#filter-grid"),
  properties: document.querySelector("#properties"),
  status: document.querySelector("#status"),
  template: document.querySelector("#property-template")
};

function setLoading(isLoading) {
  state.loading = isLoading;
  document.body.classList.toggle("loading", isLoading);
  els.uf.disabled = isLoading;
  els.cityTrigger.disabled = isLoading || !state.uf;
  els.neighborhoodTrigger.disabled = isLoading || !state.uf;
  els.modalityTrigger.disabled = isLoading;
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
    currency: "BRL"
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

async function api(path, params) {
  const response = await fetch(`${API_BASE}${path}${qs(params)}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
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
    sort: state.sort
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
    updateTrigger(els.cityTrigger, state.cities, "Todas", "selecionadas");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar cidade" });

  renderOptions(els.neighborhoodPanel, "neighborhood", data.neighborhoods, state.neighborhoods, () => {
    state.neighborhoods = readChecked(els.neighborhoodPanel);
    updateTrigger(els.neighborhoodTrigger, state.neighborhoods, "Todos", "selecionados");
    scheduleSearch();
  }, { placeholder: "Digite para buscar bairro" });

  renderOptions(els.modalityPanel, "modalidade", data.modalidades, state.modalidades, async () => {
    state.modalidades = readChecked(els.modalityPanel);
    updateTrigger(els.modalityTrigger, state.modalidades, "Todas", "selecionadas");
    await loadFilters();
    scheduleSearch();
  }, { placeholder: "Digite para buscar modalidade" });

  els.cityTrigger.disabled = state.loading || !state.uf;
  els.neighborhoodTrigger.disabled = state.loading || !state.uf;
  updateTrigger(els.cityTrigger, state.cities, "Todas", "selecionadas");
  updateTrigger(els.neighborhoodTrigger, state.neighborhoods, "Todos", "selecionados");
  updateTrigger(els.modalityTrigger, state.modalidades, "Todas", "selecionadas");
}

function renderProperties(properties) {
  els.properties.innerHTML = "";

  if (!properties.length) {
    setStatus("Nenhum imovel encontrado para estes filtros.");
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
    node.querySelector(".city").textContent = payload.Cidade || "-";
    node.querySelector(".modality").textContent = payload["Modalidade de venda"] || "-";
    node.querySelector(".neighborhood").textContent = payload.Bairro || "-";
    node.querySelector(".address").textContent = payload["Endereço"] || payload["EndereÃ§o"] || "";
    node.querySelector(".valuation").textContent = `R$ ${payload["Valor de avaliação"] || payload["Valor de avaliaÃ§Ã£o"] || "-"}`;
    node.querySelector(".price").textContent = `R$ ${payload["Preço"] || payload["PreÃ§o"] || "-"}`;
    node.querySelector(".description").textContent = payload["Descrição"] || payload["DescriÃ§Ã£o"] || "";

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
      api("/properties", { ...selectedParams(), limit: 48 })
    ]);

    els.statsTotal.textContent = formatNumber(stats.total);
    els.statsCities.textContent = formatNumber(stats.cities);
    els.statsAverage.textContent = formatMoney(filteredStats.average);
    els.statsMedian.textContent = formatMoney(filteredStats.median);
    els.lastUpdated.textContent = stats.last_updated || "-";
    renderProperties(properties);
  } catch (error) {
    setStatus("Nao foi possivel carregar os dados. Confira a URL da API.");
  }
}

async function search() {
  els.searchButton.disabled = true;
  try {
    await loadStatsAndProperties();
  } finally {
    els.searchButton.disabled = state.loading;
  }
}

function bindEvents() {
  setupPanel(els.cityTrigger, els.cityPanel);
  setupPanel(els.neighborhoodTrigger, els.neighborhoodPanel);
  setupPanel(els.modalityTrigger, els.modalityPanel);

  document.addEventListener("click", closePanels);

  els.uf.addEventListener("change", async () => {
    state.uf = els.uf.value;
    state.cities = [];
    state.neighborhoods = [];
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
    state.sort = "price_asc";
    await loadFilters();
    await search();
  });

  els.searchButton.addEventListener("click", search);
  els.toggleFilters.addEventListener("click", () => {
    els.filterGrid.hidden = !els.filterGrid.hidden;
  });
}

async function init() {
  setLoading(true);
  setStatus("Carregando filtros e estatisticas...");
  bindEvents();
  try {
    await loadFilters();
    await search();
  } finally {
    setLoading(false);
  }
}

init();
