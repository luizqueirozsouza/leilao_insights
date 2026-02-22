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

async function test() {
  console.log("Testando conexão PostgreSQL...");
  try {
    const res = await pool.query(
      "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'",
    );
    console.log("TABELAS:", res.rows);
  } catch (err) {
    console.error("ERRO:", err.message);
  } finally {
    process.exit();
  }
}

test();
