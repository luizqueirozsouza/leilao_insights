const express = require("express");
const duckdb = require("duckdb");
const cors = require("cors");
const path = require("path");

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json());

const dbPath = path.resolve(__dirname, "../data/caixa.duckdb");
console.log("📂 BD:", dbPath);

const db = new duckdb.Database(dbPath);

let cache = {
  stats: { total: 0, ufs: 0, cities: 0 },
  filters: { ufs: [], cidades: {}, bairros: {}, modalidades: [] },
  ready: false,
};

function loadData() {
  console.log("⏳ Lendo base de dados...");
  db.all("SELECT uf, payload_json FROM current_imoveis", (err, rows) => {
    if (err) {
      console.error("❌ Erro no banco:", err);
      return;
    }
    const ufs = new Set();
    const cities = new Set();
    const mods = new Set();
    const cByUf = {};
    const bByC = {};

    rows.forEach((r) => {
      ufs.add(r.uf);
      if (!cByUf[r.uf]) cByUf[r.uf] = new Set();
      try {
        const p = JSON.parse(r.payload_json);
        if (p.Cidade) {
          cities.add(p.Cidade);
          cByUf[r.uf].add(p.Cidade);
          const k = `${r.uf}|${p.Cidade}`;
          if (!bByC[k]) bByC[k] = new Set();
          if (p.Bairro) bByC[k].add(p.Bairro);
        }
        if (p["Modalidade de venda"]) mods.add(p["Modalidade de venda"]);
      } catch (e) {}
    });

    cache.stats = { total: rows.length, ufs: ufs.size, cities: cities.size };
    cache.filters.ufs = Array.from(ufs).sort();
    cache.filters.modalidades = Array.from(mods).sort();
    for (const u in cByUf)
      cache.filters.cidades[u] = Array.from(cByUf[u]).sort();
    for (const k in bByC) cache.filters.bairros[k] = Array.from(bByC[k]).sort();

    cache.ready = true;
    console.log("✅ Pronto:", rows.length, "imóveis");
  });
}

loadData();

app.get("/api/stats", (req, res) => res.json(cache.stats));
app.get("/api/filters", (req, res) => {
  const { uf, city } = req.query;
  res.json({
    ufs: cache.filters.ufs,
    modalidades: cache.filters.modalidades,
    cities: uf ? cache.filters.cidades[uf] || [] : [],
    neighborhoods:
      uf && city ? cache.filters.bairros[`${uf}|${city}`] || [] : [],
  });
});

app.get("/api/properties", (req, res) => {
  const { uf, city, neighborhood, modalidade, limit = 20 } = req.query;
  let q = "SELECT uf, payload_json FROM current_imoveis WHERE 1=1";
  const p = [];
  if (uf) {
    q += " AND uf = ?";
    p.push(uf);
  }
  db.all(q, p, (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    let resRows = rows.map((r) => ({
      uf: r.uf,
      payload: JSON.parse(r.payload_json),
    }));
    if (city) resRows = resRows.filter((r) => r.payload.Cidade === city);
    if (neighborhood)
      resRows = resRows.filter((r) => r.payload.Bairro === neighborhood);
    if (modalidade)
      resRows = resRows.filter(
        (r) => r.payload["Modalidade de venda"] === modalidade,
      );
    res.json(resRows.slice(0, Number(limit)));
  });
});

app.listen(port, () => console.log(`🚀 http://localhost:${port}`));
