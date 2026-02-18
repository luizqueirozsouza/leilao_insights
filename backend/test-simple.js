const duckdb = require("duckdb");
const path = require("path");

const dbPath = path.resolve(__dirname, "../data/caixa.duckdb");
const db = new duckdb.Database(dbPath);

console.log("Testando query simples...");
db.all("SELECT count(*) as total FROM current_imoveis", (err, rows) => {
  if (err) {
    console.error("ERRO:", err);
    process.exit(1);
  }
  console.log("TOTAL:", rows[0].total);
  process.exit(0);
});
