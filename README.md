# Leilao Insights

O `app_leilao` centraliza a captura diaria dos imoveis da Caixa, atualiza o PostgreSQL e disponibiliza esses dados para consulta no frontend e no dashboard.

Hoje, o fluxo oficial do projeto usa:
- `extrai.py` para baixar os CSVs da Caixa
- `ingest.py` para comparar com o estado atual e atualizar o PostgreSQL
- backend Node.js + Express + TypeScript para servir a API
- frontend React + Vite para a busca
- dashboard Streamlit para analise operacional

## Arquitetura

1. A Caixa publica os CSVs por UF.
2. O projeto baixa os arquivos para `data/caixa/dt=AAAA-MM-DD`.
3. O `ingest.py` valida os arquivos do dia, compara com `current_imoveis`, grava eventos em `changes` e reconstrui `current_imoveis`.
4. O backend le o PostgreSQL e entrega os dados para o frontend.

## Banco de dados

O banco principal do projeto e o PostgreSQL.

Tabelas principais:
- `snapshot_imoveis`: snapshot bruto da carga do dia
- `current_imoveis`: estado atual da base
- `changes`: eventos `ENTER`, `EXIT` e `UPDATE`

Observacao:
- `data/caixa.duckdb` e scripts antigos com DuckDB nao fazem parte do fluxo principal atual.

## Fluxo de atualizacao

O fluxo atual funciona assim:

1. `extrai.py` baixa os CSVs mais recentes da Caixa.
2. `ingest.py` exige que todas as UFs tenham sido baixadas.
3. O script compara a nova carga com `current_imoveis`.
4. O script atualiza `changes`.
5. O script reconstrui `current_imoveis` para refletir exatamente a ultima carga valida.
6. Depois da carga, os CSVs antigos podem ser removidos.

## Requisitos locais

- Node.js 20+
- Python 3.13+
- `uv` instalado
- acesso ao PostgreSQL configurado no `.env`

## Variaveis de ambiente

Crie ou ajuste o arquivo `.env` na raiz:

```env
host=SEU_HOST_POSTGRES
port=5432
database="db_leiloes"
user="postgres"
password="SUA_SENHA"
sslmode="disable"
SERVER_PORT=3001
```

Para o frontend local, use `frontend/.env.local`:

```env
VITE_API_BASE=http://localhost:3001/api
```

## Como executar localmente

### 1. Instalar dependencias Python

Na raiz do projeto:

```bash
uv sync
```

### 2. Subir o backend

```bash
cd backend
npm install
npm run dev
```

Teste a API:

```text
http://localhost:3001/api/stats
```

### 3. Subir o frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend local:

```text
http://localhost:5173
```

### 4. Subir o dashboard Streamlit

Opcional:

```bash
uv run streamlit run app.py
```

Dashboard local:

```text
http://localhost:8501
```

## Como atualizar o banco localmente

Na raiz do projeto:

```bash
uv run python extrai.py
uv run python ingest.py
```

Resultado esperado:
- os CSVs do dia sao baixados para `data/caixa/dt=AAAA-MM-DD`
- o PostgreSQL e atualizado
- a API passa a refletir a nova base

## Validacao rapida depois da carga

1. Teste a API:

```text
http://localhost:3001/api/stats
```

2. Verifique se o frontend carrega filtros e resultados.

3. Se quiser verificar direto no banco:

```sql
select count(*) from current_imoveis;
```

## Automacao diaria

O repositorio possui um fluxo inicial do Kestra em:

[`kestra/caixa_daily_sync.yaml`](./kestra/caixa_daily_sync.yaml)

Esse fluxo:
- baixa os CSVs do dia
- executa a ingestao
- valida o volume final em `current_imoveis`
- remove diretorios antigos de CSV

Antes de usar em producao, ajuste:
- caminho do repositorio na VPS
- horario do agendamento
- politica de limpeza
- notificacoes

## Docker

Para subir a stack com Docker Compose:

```bash
docker compose up -d --build
```

Servicos:
- backend
- frontend
- dashboard

## Observacoes operacionais

- O backend em desenvolvimento precisa ler o `.env` da raiz do projeto.
- Se a API responder erro e o banco estiver correto, valide primeiro `http://localhost:3001/api/stats`.
- O frontend depende de `VITE_API_BASE` para apontar para a API correta.
- Os CSVs antigos nao precisam ficar acumulados depois da carga bem-sucedida.

## Tecnologias

- Python
- PostgreSQL
- Node.js
- Express
- TypeScript
- React
- Vite
- Streamlit
- Kestra
