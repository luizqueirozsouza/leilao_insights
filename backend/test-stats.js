const duckdb = require("duckdb");
const path = require("path");

const dbPath = path.resolve(__dirname, "../data/caixa.duckdb");
const db = new duckdb.Database(dbPath);

const query = `
    SELECT 
      count(*) as total,
      count(distinct uf) as ufs,
      count(distinct json_extract_path_text(payload_json, '$.Cidade')) as cities
    FROM current_imoveis
`;

console.log("Executando query...");
db.all(query, (err, rows) => {
  if (err) {
    console.error("ERRO:", err);
    process.exit(1);
  }
  console.log("RESULTADO:", JSON.stringify(rows[0]));
  process.exit(0);
});
