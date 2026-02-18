const duckdb = require("duckdb");
const path = require("path");

const dbPath = path.resolve(__dirname, "../data/caixa.duckdb");
console.log("Tentando conectar ao banco em:", dbPath);

const db = new duckdb.Database(dbPath);

db.all("SELECT count(*) as count FROM current_imoveis", (err, rows) => {
  if (err) {
    console.error("ERRO AO ACESSAR BANCO:", err);
    process.exit(1);
  }
  console.log("CONEXÃO OK! Registros encontrados:", rows[0].count);
  process.exit(0);
});
