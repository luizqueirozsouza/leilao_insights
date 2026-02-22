const express = require("express");
const { Pool } = require("pg");
const cors = require("cors");
const path = require("path");
const dotenv = require("dotenv");

// Carregar variáveis de ambiente
dotenv.config({ path: path.join(__dirname, "..", ".env") });

const app = express();
const port = process.env.SERVER_PORT || 3001;

app.use(cors());
app.use(express.json());

// Configuração do Banco de Dados
const pool = new Pool({
  host: process.env.host,
  port: process.env.port,
  user: (process.env.user || "").replace(/"/g, ""),
  password: (process.env.password || "").replace(/"/g, ""),
  database: (process.env.database || "db_leiloes").replace(/"/g, ""),
  ssl:
    process.env.sslmode === "require" ? { rejectUnauthorized: false } : false,
});

let cache = {
  stats: { total: 0, ufs: 0, cities: 0 },
  filters: { ufs: [], cidades: {}, bairros: {}, modalidades: [] },
  ready: false,
};

async function loadData() {
  console.log("⏳ Lendo base de dados PostgreSQL...");
  try {
    const res = await pool.query(
      "SELECT uf, payload_json FROM current_imoveis",
    );
    const rows = res.rows;

    const ufs = new Set();
    const cities = new Set();
    const mods = new Set();
    const cByUf = {};
    const bByC = {};

    rows.forEach((r) => {
      ufs.add(r.uf);
      if (!cByUf[r.uf]) cByUf[r.uf] = new Set();

      const p =
        typeof r.payload_json === "string"
          ? JSON.parse(r.payload_json)
          : r.payload_json;

      if (p.Cidade) {
        cities.add(p.Cidade);
        cByUf[r.uf].add(p.Cidade);
        const k = `${r.uf}|${p.Cidade}`;
        if (!bByC[k]) bByC[k] = new Set();
        if (p.Bairro) bByC[k].add(p.Bairro);
      }
      if (p["Modalidade de venda"]) mods.add(p["Modalidade de venda"]);
    });

    cache.stats = { total: rows.length, ufs: ufs.size, cities: cities.size };
    cache.filters.ufs = Array.from(ufs).sort();
    cache.filters.modalidades = Array.from(mods).sort();
    for (const u in cByUf)
      cache.filters.cidades[u] = Array.from(cByUf[u]).sort();
    for (const k in bByC) cache.filters.bairros[k] = Array.from(bByC[k]).sort();

    cache.ready = true;
    console.log("✅ Pronto:", rows.length, "imóveis");
  } catch (err) {
    console.error("❌ Erro no banco:", err);
  }
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

app.get("/api/properties", async (req, res) => {
  const { uf, city, neighborhood, modalidade, limit = 20 } = req.query;
  try {
    let q = "SELECT uf, payload_json FROM current_imoveis WHERE 1=1";
    const values = [];
    if (uf) {
      q += " AND uf = $1";
      values.push(uf);
    }

    const { rows } = await pool.query(q, values);
    let resRows = rows.map((r) => ({
      uf: r.uf,
      payload:
        typeof r.payload_json === "string"
          ? JSON.parse(r.payload_json)
          : r.payload_json,
    }));

    if (city) resRows = resRows.filter((r) => r.payload.Cidade === city);
    if (neighborhood)
      resRows = resRows.filter((r) => r.payload.Bairro === neighborhood);
    if (modalidade)
      resRows = resRows.filter(
        (r) => r.payload["Modalidade de venda"] === modalidade,
      );
    res.json(resRows.slice(0, Number(limit)));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(port, () => console.log(`🚀 http://localhost:${port}`));
