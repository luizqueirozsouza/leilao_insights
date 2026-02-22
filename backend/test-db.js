const { Pool } = require("pg");
const path = require("path");
const dotenv = require("dotenv");

dotenv.config({ path: path.join(__dirname, "..", ".env") });

const pool = new Pool({
  host: process.env.host,
  port: process.env.port,
  user: (process.env.user || "").replace(/"/g, ""),
  password: (process.env.password || "").replace(/"/g, ""),
  database: (process.env.database || "db_leiloes").replace(/"/g, ""),
  ssl:
    process.env.sslmode === "require" ? { rejectUnauthorized: false } : false,
});

async function run() {
  console.log("Tentando conectar ao Postgres em:", process.env.host);
  try {
    const { rows } = await pool.query(
      "SELECT count(*) as count FROM current_imoveis",
    );
    console.log("CONEXÃO OK! Registros encontrados:", rows[0].count);
    process.exit(0);
  } catch (err) {
    console.error("ERRO AO ACESSAR BANCO:", err.message);
    process.exit(1);
  }
}

run();
