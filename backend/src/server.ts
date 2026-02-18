import express from "express";
import { Pool } from "pg";
import cors from "cors";
import path from "path";
import dotenv from "dotenv";

// Carregar variáveis de ambiente (o .env é opcional em produção)
dotenv.config();
dotenv.config({ path: path.join(__dirname, "..", ".env") });

const app = express();
const port = Number(process.env.SERVER_PORT) || 3001;

app.use(cors());
app.use(express.json());

// Configuração do Banco de Dados com Fallback para maiúsculas (padrão Docker/Easypanel)
const dbConfig = {
  host: process.env.host || process.env.DB_HOST || process.env.POSTGRES_HOST,
  port: Number(process.env.port || process.env.DB_PORT || 5432),
  user: (process.env.user || process.env.DB_USER || "postgres").replace(
    /"/g,
    "",
  ),
  password: (process.env.password || process.env.DB_PASSWORD || "").replace(
    /"/g,
    "",
  ),
  database: (
    process.env.database ||
    process.env.DB_NAME ||
    "db_leiloes"
  ).replace(/"/g, ""),
  ssl:
    process.env.sslmode === "require" ? { rejectUnauthorized: false } : false,
};

const pool = new Pool(dbConfig);

console.log(
  `📂 Tentando conectar ao Postgres em: ${dbConfig.host}:${dbConfig.port}`,
);
console.log(`👤 Usuário DB: ${dbConfig.user}`);

interface FilterItem {
  label: string;
  value: string;
  count: number;
}

interface Cache {
  stats: { total: number; ufs: number; cities: number };
  filters: {
    ufs: FilterItem[];
    modalidades: FilterItem[];
    cidades: Record<string, FilterItem[]>;
    bairros: Record<string, FilterItem[]>;
  };
  ready: boolean;
}

const cache: Cache = {
  stats: { total: 0, ufs: 0, cities: 0 },
  filters: { ufs: [], cidades: {}, bairros: {}, modalidades: [] },
  ready: false,
};

async function loadData() {
  console.log("⏳ Lendo base de dados PostgreSQL...");
  try {
    const { rows } = await pool.query(
      "SELECT uf, numero_imovel, payload_json FROM current_imoveis",
    );

    const ufsMap = new Map<string, number>();
    const modsMap = new Map<string, number>();
    const citiesCountMap = new Map<string, number>(); // total cities count

    const cByUfMap: Record<string, Map<string, number>> = {};
    const bByCMap: Record<string, Map<string, number>> = {};

    rows.forEach((r: any) => {
      const uf = String(r.uf);
      ufsMap.set(uf, (ufsMap.get(uf) || 0) + 1);

      if (!cByUfMap[uf]) cByUfMap[uf] = new Map();

      const p =
        typeof r.payload_json === "string"
          ? JSON.parse(r.payload_json)
          : r.payload_json;

      if (p.Cidade) {
        const cidade = String(p.Cidade);
        citiesCountMap.set(cidade, 1);
        cByUfMap[uf].set(cidade, (cByUfMap[uf].get(cidade) || 0) + 1);

        const key = `${uf}|${cidade}`;
        if (!bByCMap[key]) bByCMap[key] = new Map();
        if (p.Bairro) {
          const bairro = String(p.Bairro);
          bByCMap[key].set(bairro, (bByCMap[key].get(bairro) || 0) + 1);
        }
      }
      if (p["Modalidade de venda"]) {
        const mod = String(p["Modalidade de venda"]);
        modsMap.set(mod, (modsMap.get(mod) || 0) + 1);
      }
    });

    const toFilterItems = (map: Map<string, number>) =>
      Array.from(map.entries())
        .map(([val, count]) => ({ label: val, value: val, count }))
        .sort((a, b) => a.label.localeCompare(b.label));

    cache.stats = {
      total: rows.length,
      ufs: ufsMap.size,
      cities: citiesCountMap.size,
    };
    cache.filters.ufs = toFilterItems(ufsMap);
    cache.filters.modalidades = toFilterItems(modsMap);

    for (const u in cByUfMap) {
      cache.filters.cidades[u] = toFilterItems(cByUfMap[u]);
    }
    for (const k in bByCMap) {
      cache.filters.bairros[k] = toFilterItems(bByCMap[k]);
    }

    cache.ready = true;
    console.log(
      `✅ Sistema pronto. ${rows.length} imóveis carregados com insights.`,
    );
  } catch (err) {
    console.error("❌ Erro fatal no banco:", err);
  }
}

// Carregar dados inicialmente
loadData();

// Tentar recarregar a cada 5 minutos caso não haja dados
setInterval(() => {
  if (!cache.ready || cache.stats.total === 0) {
    loadData();
  }
}, 300000);

app.get("/api/stats", (req, res) => res.json(cache.stats));

app.get("/api/filters", (req, res) => {
  const { uf, city } = req.query;
  const ufStr = uf ? String(uf) : "";
  const cityStr = city ? String(city) : "";

  res.json({
    ufs: cache.filters.ufs,
    modalidades: cache.filters.modalidades,
    cities: ufStr ? cache.filters.cidades[ufStr] || [] : [],
    neighborhoods: (() => {
      if (!ufStr || !cityStr) return [];
      const cities = cityStr.split(",");
      if (cities.length === 1) {
        return cache.filters.bairros[`${ufStr}|${cityStr}`] || [];
      }

      // Combinar bairros de múltiplas cidades
      const combined = new Map<string, FilterItem>();
      cities.forEach((c) => {
        const bairros = cache.filters.bairros[`${ufStr}|${c}`] || [];
        bairros.forEach((b) => {
          if (combined.has(b.value)) {
            const existing = combined.get(b.value)!;
            combined.set(b.value, {
              ...existing,
              count: existing.count + b.count,
            });
          } else {
            combined.set(b.value, b);
          }
        });
      });
      return Array.from(combined.values()).sort((a, b) =>
        a.label.localeCompare(b.label),
      );
    })(),
  });
});

app.get("/api/stats/filtered", async (req, res) => {
  const { uf, city, neighborhood, modalidade } = req.query;
  try {
    let q = `
      SELECT 
        AVG(CAST(replace(replace(payload_json->>'Valor de avaliação', '.', ''), ',', '.') AS NUMERIC)) as average,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST(replace(replace(payload_json->>'Valor de avaliação', '.', ''), ',', '.') AS NUMERIC)) as median
      FROM current_imoveis 
      WHERE 1=1`;
    const p: any[] = [];
    let paramIndex = 1;

    if (uf) {
      q += ` AND uf = $${paramIndex++}`;
      p.push(uf);
    }
    if (city) {
      const cities = String(city).split(",");
      if (cities.length > 1) {
        q += ` AND payload_json->>'Cidade' IN (${cities.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...cities);
      } else {
        q += ` AND payload_json->>'Cidade' = $${paramIndex++}`;
        p.push(city);
      }
    }
    if (neighborhood) {
      const neighborhoods = String(neighborhood).split(",");
      if (neighborhoods.length > 1) {
        q += ` AND payload_json->>'Bairro' IN (${neighborhoods.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...neighborhoods);
      } else {
        q += ` AND payload_json->>'Bairro' = $${paramIndex++}`;
        p.push(neighborhood);
      }
    }
    if (modalidade) {
      const modalidades = String(modalidade).split(",");
      if (modalidades.length > 1) {
        q += ` AND payload_json->>'Modalidade de venda' IN (${modalidades.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...modalidades);
      } else {
        q += ` AND payload_json->>'Modalidade de venda' = $${paramIndex++}`;
        p.push(modalidade);
      }
    }

    const { rows } = await pool.query(q, p);
    res.json({
      average: Number(rows[0].average || 0),
      median: Number(rows[0].median || 0),
    });
  } catch (err) {
    res.status(500).json({ error: "Erro ao calcular estatísticas" });
  }
});

app.get("/api/properties", async (req, res) => {
  const { uf, city, neighborhood, modalidade, sort, limit = 24 } = req.query;
  try {
    let q =
      "SELECT uf, numero_imovel, payload_json FROM current_imoveis WHERE 1=1";
    const p: any[] = [];
    let paramIndex = 1;

    if (uf) {
      q += ` AND uf = $${paramIndex++}`;
      p.push(uf);
    }

    // Como o payload_json é JSONB no Postgres, podemos filtrar direto no SQL para maior performance
    // Mas para manter compatibilidade com o código anterior que fazia no JS, vou deixar o SQL base e filtrar no JS
    // OU filtrar no SQL se for simples:
    if (city) {
      const cities = String(city).split(",");
      if (cities.length > 1) {
        q += ` AND payload_json->>'Cidade' IN (${cities.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...cities);
      } else {
        q += ` AND payload_json->>'Cidade' = $${paramIndex++}`;
        p.push(city);
      }
    }
    if (neighborhood) {
      const neighborhoods = String(neighborhood).split(",");
      if (neighborhoods.length > 1) {
        q += ` AND payload_json->>'Bairro' IN (${neighborhoods.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...neighborhoods);
      } else {
        q += ` AND payload_json->>'Bairro' = $${paramIndex++}`;
        p.push(neighborhood);
      }
    }
    if (modalidade) {
      const modalidades = String(modalidade).split(",");
      if (modalidades.length > 1) {
        q += ` AND payload_json->>'Modalidade de venda' IN (${modalidades.map(() => `$${paramIndex++}`).join(",")})`;
        p.push(...modalidades);
      } else {
        q += ` AND payload_json->>'Modalidade de venda' = $${paramIndex++}`;
        p.push(modalidade);
      }
    }

    if (sort === "price_asc") {
      q +=
        " ORDER BY CAST(replace(replace(payload_json->>'Preço', '.', ''), ',', '.') AS NUMERIC) ASC";
    } else if (sort === "price_desc") {
      q +=
        " ORDER BY CAST(replace(replace(payload_json->>'Preço', '.', ''), ',', '.') AS NUMERIC) DESC";
    }

    q += ` LIMIT $${paramIndex++}`;
    p.push(Number(limit));

    const { rows } = await pool.query(q, p);

    const resRows = rows.map((r: any) => ({
      uf: r.uf,
      numero_imovel: r.numero_imovel,
      payload:
        typeof r.payload_json === "string"
          ? JSON.parse(r.payload_json)
          : r.payload_json,
    }));

    res.json(resRows);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(port, "0.0.0.0", () =>
  console.log(`🚀 Script Backend rodando em http://localhost:${port}`),
);
