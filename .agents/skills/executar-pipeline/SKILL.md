---
name: executar-pipeline
description: Execute, test, and debug the data pipeline for Caixa auctions (downloading, ingesting, and syncing). Use this skill whenever the user asks to run, test, sync, or trigger the data pipeline, including Django commands (sync_auctions, extrai_auctions, ingest_auctions), standalone scripts (extrai.py, ingest.py), or the daily DLT pipeline (pipeline/run_daily_pipeline.py).
---

# Executar Pipeline de Leilões

Esta skill fornece instruções para a execução, teste e depuração do pipeline de atualização de dados de leilões da Caixa Econômica Federal.

## 📋 Pré-requisitos

1. **PostgreSQL**: O banco de dados deve estar rodando (não há suporte para SQLite).
2. **Ambiente Python**: Ter o `uv` instalado e dependências sincronizadas:
   ```bash
   uv sync
   ```
3. **Arquivo `.env`**: Deve existir na raiz do repositório contendo as credenciais do banco e variáveis do pipeline:
   ```env
   host=localhost
   port=5432
   database="db_leiloes"
   user="postgres"
   password="..."
   SECRET_KEY="..."
   DEBUG=True
   CORS_ALLOWED_ORIGINS=http://localhost:8000
   ```

---

## 🚀 Como Executar o Pipeline

Você pode executar o pipeline utilizando Comandos do Django, Scripts Standalone ou o Pipeline Diário (DLT).

### 1. Comandos de Gerenciamento do Django (Recomendado)

Os comandos do Django são executados dentro do contexto do projeto Django (`backend_django`).

* **Sincronização Completa (Download + Ingestão)**:
  ```bash
  uv run python backend_django/manage.py sync_auctions --date YYYY-MM-DD --verbose
  ```
* **Apenas Download (Extração)**:
  ```bash
  uv run python backend_django/manage.py extrai_auctions --date YYYY-MM-DD --verbose
  ```
* **Apenas Ingestão (Carga)**:
  ```bash
  uv run python backend_django/manage.py ingest_auctions --date YYYY-MM-DD --verbose
  ```

> [!IMPORTANT]
> **Comportamento de limpeza de CSV**: Os comandos de gerenciamento do Django **deletam os arquivos CSV temporários por padrão** após uma ingestão bem-sucedida. Se você deseja manter os arquivos para análise, adicione a flag `--keep-csv`.

---

### 2. Scripts Standalone (Alternativa rápida)

Esses scripts executam de forma independente do framework Django.

* **Apenas Download (Extração)**:
  ```bash
  uv run python extrai.py --date YYYY-MM-DD --verbose
  ```
* **Apenas Ingestão (Carga)**:
  ```bash
  uv run python ingest.py --date YYYY-MM-DD --verbose
  ```

> [!IMPORTANT]
> **Comportamento de limpeza de CSV**: Os scripts standalone **mantêm os arquivos CSV por padrão**. Para apagá-los após o término da ingestão, você deve passar explicitamente a flag `--delete-csv`:
> ```bash
> uv run python ingest.py --date YYYY-MM-DD --verbose --delete-csv
> ```

---

### 3. Pipeline Diário DLT (Produção / VPS)

Executa a pipeline de dados utilizando dlt (data load tool) e dispara notificações para o Telegram (se configurado).
```bash
uv run python pipeline/run_daily_pipeline.py --verbose
```

---

## ⚠️ Regras e Detalhes Importantes

* **Ingestão Completa de UFs**: O processo de ingestão irá abortar imediatamente se não encontrar os arquivos CSV de **todas as 27 UFs brasileiras** no diretório `data/`.
* **Local de Execução (Evitar Bloqueios)**: O site da Caixa pode bloquear requisições vindas de faixas de IP de servidores VPS comuns (retornando erro 403). Por isso, o download (`extrai`) costuma ser executado localmente ou em runners de CI (GitHub Actions) antes de enviar os dados para o servidor de produção.
* **Tabelas do Banco de Dados**:
  * `snapshot_imoveis`: Carga bruta diária dos CSVs (acessada via SQL bruto em `ingest.py` e `ingest_auctions`).
  * `current_imoveis` (Model `Auction`): Estado consolidado atualizado dos leilões usado pela API.
  * `changes` (Model `AuctionEvent`): Eventos de mudanças identificados (`ENTER`, `EXIT`, `UPDATE`).
