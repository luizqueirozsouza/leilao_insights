const duckdb = require("duckdb");
const path = require("path");
const dbPath = path.resolve(__dirname, "../data/caixa.duckdb");
const db = new duckdb.Database(dbPath);

console.log("Testando conexão...");
db.all("PRAGMA show_tables", (err, rows) => {
  if (err) {
    console.error("ERRO:", err);
  } else {
    console.log("TABELAS:", rows);
  }
  process.exit();
});
