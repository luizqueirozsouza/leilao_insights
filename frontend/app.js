const API_BASE = (window.LEILAO_CONFIG && window.LEILAO_CONFIG.API_BASE) || "/api";

const state = {
  uf: "",
  cities: [],
  neighborhoods: [],
  modalidades: [],
  sort: "price_asc"
};

const els = {
  statsTotal: document.querySelector("#stat-total"),
  statsCities: document.querySelector("#stat-cities"),
  statsAverage: document.querySelector("#stat-average"),
  statsMedian: document.querySelector("#stat-median"),
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

function renderOptions(panel, groupName, options, selectedValues, onChange) {
  panel.innerHTML = "";
  if (!options.length) {
    const empty = document.createElement("div");
    empty.className = "status";
    empty.textContent = "Nenhuma opcao disponivel.";
    panel.appendChild(empty);
    return;
  }

  options.forEach((option) => {
    const label = document.createElement("label");
    label.className = "option-row";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = groupName;
    input.value = option.value;
    input.checked = selectedValues.includes(option.value);
    input.addEventListener("change", onChange);

    const text = document.createElement("span");
    text.textContent = option.label;

    const count = document.createElement("small");
    count.textContent = formatNumber(option.count);

    label.append(input, text, count);
    panel.appendChild(label);
  });
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
  });
  panel.addEventListener("click", (event) => event.stopPropagation());
}

async function loadFilters() {
  const data = await api("/filters", selectedParams());

  els.uf.innerHTML = '<option value="">Todos</option>';
  data.ufs.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.label} (${formatNumber(item.count)})`;
    option.selected = item.value === state.uf;
    els.uf.appendChild(option);
  });

  renderOptions(els.cityPanel, "city", data.cities, state.cities, async () => {
    state.cities = readChecked(els.cityPanel);
    state.neighborhoods = [];
    updateTrigger(els.cityTrigger, state.cities, "Todas", "selecionadas");
    await loadFilters();
  });

  renderOptions(els.neighborhoodPanel, "neighborhood", data.neighborhoods, state.neighborhoods, () => {
    state.neighborhoods = readChecked(els.neighborhoodPanel);
    updateTrigger(els.neighborhoodTrigger, state.neighborhoods, "Todos", "selecionados");
  });

  renderOptions(els.modalityPanel, "modalidade", data.modalidades, state.modalidades, async () => {
    state.modalidades = readChecked(els.modalityPanel);
    updateTrigger(els.modalityTrigger, state.modalidades, "Todas", "selecionadas");
    await loadFilters();
  });

  els.cityTrigger.disabled = !state.uf;
  els.neighborhoodTrigger.disabled = !state.uf;
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
  els.searchButton.disabled = true;
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
    renderProperties(properties);
  } catch (error) {
    setStatus("Nao foi possivel carregar os dados. Confira a URL da API.");
  } finally {
    els.searchButton.disabled = false;
  }
}

async function search() {
  await loadStatsAndProperties();
}

function bindEvents() {
  setupPanel(els.cityTrigger, els.cityPanel);
  setupPanel(els.neighborhoodTrigger, els.neighborhoodPanel);
  setupPanel(els.modalityTrigger, els.modalityPanel);

  document.addEventListener("click", () => {
    document.querySelectorAll(".multi-panel.open").forEach((item) => item.classList.remove("open"));
  });

  els.uf.addEventListener("change", async () => {
    state.uf = els.uf.value;
    state.cities = [];
    state.neighborhoods = [];
    await loadFilters();
  });

  els.sortButton.addEventListener("click", () => {
    state.sort = state.sort === "price_asc" ? "price_desc" : "price_asc";
    els.sortButton.textContent = state.sort === "price_asc" ? "Menor preco" : "Maior preco";
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
  bindEvents();
  await loadFilters();
  await search();
}

init();
