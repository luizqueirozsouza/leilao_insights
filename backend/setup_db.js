const { Client } = require("pg");
const dotenv = require("dotenv");
const path = require("path");

dotenv.config({ path: path.join(__dirname, "..", ".env") });

console.log("Dados de Conexão:", {
  host: process.env.host,
  user: process.env.user,
  database: process.env.database,
});

async function setup() {
  const adminConfig = {
    host: process.env.host,
    port: process.env.port,
    user: process.env.user?.replace(/"/g, ""),
    password: process.env.password?.replace(/"/g, ""),
    database: "postgres",
    ssl:
      process.env.sslmode === "require" ? { rejectUnauthorized: false } : false,
  };

  const adminClient = new Client(adminConfig);

  try {
    await adminClient.connect();
    console.log('✅ Conectado ao banco "postgres"');

    const res = await adminClient.query(
      "SELECT 1 FROM pg_database WHERE datname = 'db_leiloes'",
    );
    if (res.rowCount === 0) {
      console.log('⏳ Criando banco de dados "db_leiloes"...');
      await adminClient.query("CREATE DATABASE db_leiloes");
      console.log('✅ Banco "db_leiloes" criado com sucesso.');
    } else {
      console.log('ℹ️ Banco "db_leiloes" já existe.');
    }
  } catch (err) {
    console.error("❌ Erro no admin setup:", err.message);
    // Não encerramos aqui se o erro for apenas permissão, talvez o banco já exista e possamos prosseguir
  } finally {
    try {
      await adminClient.end();
    } catch (e) {}
  }

  const dbConfig = {
    host: process.env.host,
    port: process.env.port,
    user: process.env.user?.replace(/"/g, ""),
    password: process.env.password?.replace(/"/g, ""),
    database: "db_leiloes",
    ssl:
      process.env.sslmode === "require" ? { rejectUnauthorized: false } : false,
  };

  const client = new Client(dbConfig);

  try {
    await client.connect();
    console.log('✅ Conectado ao banco "db_leiloes"');

    console.log("⏳ Criando tabelas...");

    await client.query(`
            CREATE TABLE IF NOT EXISTS snapshot_imoveis (
                id SERIAL PRIMARY KEY,
                dt DATE,
                uf VARCHAR(10),
                numero_imovel VARCHAR(50),
                payload_json JSONB,
                fp VARCHAR(100),
                source_file TEXT
            );
        `);

    await client.query(`
            CREATE TABLE IF NOT EXISTS current_imoveis (
                uf VARCHAR(10),
                numero_imovel VARCHAR(50),
                payload_json JSONB,
                fp VARCHAR(100),
                last_seen DATE,
                source_file TEXT,
                PRIMARY KEY (uf, numero_imovel)
            );
        `);

    await client.query(`
            CREATE TABLE IF NOT EXISTS changes (
                id SERIAL PRIMARY KEY,
                dt DATE,
                uf VARCHAR(10),
                tipo_evento VARCHAR(50),
                numero_imovel VARCHAR(50),
                changed_fields TEXT,
                before_json JSONB,
                after_json JSONB
            );
        `);

    await client.query(
      "CREATE INDEX IF NOT EXISTS idx_snapshot_dt ON snapshot_imoveis(dt);",
    );
    await client.query(
      "CREATE INDEX IF NOT EXISTS idx_changes_dt ON changes(dt);",
    );
    await client.query(
      "CREATE INDEX IF NOT EXISTS idx_snapshot_uf_num ON snapshot_imoveis(uf, numero_imovel);",
    );

    console.log("✅ Tabelas e índices criados com sucesso.");
  } catch (err) {
    console.error("❌ Erro ao configurar tabelas:", err.message);
  } finally {
    try {
      await client.end();
    } catch (e) {}
  }
}

setup();
