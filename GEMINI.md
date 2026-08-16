# GEMINI.md

Este arquivo serve como guia de referência rápida para o desenvolvimento, execução e manutenção do projeto **Leilão Insights**.

---

## 🛠️ Comandos Frequentes

### Ambiente e Dependências
O projeto utiliza o gerenciador de pacotes **uv** e requer Python 3.13+.
```bash
uv sync                                          # Instala dependências
```

### Execução dos Servidores
* **Backend Django (Porta 8000)**:
  ```bash
  uv run python backend_django/manage.py migrate    # Roda as migrações (requer PostgreSQL)
  uv run python backend_django/manage.py runserver  # Roda servidor de desenvolvimento
  ```
* **Backend FastAPI (Porta 8001 - Stubs/Endpoints de IA)**:
  ```bash
  uv run uvicorn backend_fastapi.main:app --port 8001 --reload
  ```
* **Frontend**:
  Static HTML/JS/CSS (sem etapa de build). Pode ser aberto diretamente no navegador ou via extensão Live Server. O base URL da API é configurado em `frontend/config.js` via `window.LEILAO_CONFIG.API_BASE`.

### Pipeline de Dados
* **Sincronização Completa (Django)**:
  ```bash
  uv run python backend_django/manage.py sync_auctions --date YYYY-MM-DD --verbose
  ```
* **Apenas Download (Django)**:
  ```bash
  uv run python backend_django/manage.py extrai_auctions --date YYYY-MM-DD --verbose
  ```
* **Apenas Ingestão (Django)**:
  ```bash
  uv run python backend_django/manage.py ingest_auctions --date YYYY-MM-DD --verbose
  ```
* **Scripts Standalone**:
  ```bash
  uv run python extrai.py --date YYYY-MM-DD --verbose
  uv run python ingest.py --date YYYY-MM-DD --verbose --delete-csv
  ```
* **Pipeline Diário (DLT)**:
  ```bash
  uv run python pipeline/run_daily_pipeline.py --verbose
  ```

---

## 📁 Estrutura do Repositório

- `backend_django/` — Servidor principal (Django 6 com REST API e comandos de gerência). O app label correto é `backend_django.auctions`.
- `backend_fastapi/` — API FastAPI utilizada para stubs de processamento de inteligência artificial.
- `frontend/` — Código estático do painel visual.
- `pipeline/` — Pipeline diário baseado em DLT executado via Cron na VPS.
- `extrai.py` / `ingest.py` — Scripts standalone alternativos aos comandos Django.
- `data/` — Diretório local para download temporário dos CSVs (ignorado no git).

---

## 💾 Banco de Dados (PostgreSQL)

O projeto exige o PostgreSQL (não há suporte para SQLite). Configurações de acesso devem estar presentes no arquivo `.env` na raiz do projeto.

### Tabelas Críticas
* `snapshot_imoveis`: Tabela de carga bruta diária que armazena os dados vindos dos CSVs da Caixa. Acessada via SQL bruto em `ingest.py` e `ingest_auctions`.
* `current_imoveis` (Model `Auction`): Estado atual consolidado de todos os leilões ativos exposto na API.
* `changes` (Model `AuctionEvent`): Histórico de eventos detectados (`ENTER`, `EXIT`, `UPDATE`).

---

## ⚠️ Detalhes Críticos e Regras

1. **CORS Customizado**: Configurado localmente em `backend_django.core.middleware.CorsMiddleware`. As origens permitidas devem ser declaradas via variável de ambiente `CORS_ALLOWED_ORIGINS`. Não utilizar pacotes terceiros como `django-cors-headers`.
2. **Servidor de Produção**: Roda em modo ASGI via Uvicorn (`backend_django.core.asgi`).
3. **Limpeza de CSVs temporários**:
   * Comandos de gerência Django: **Deletam por padrão**. Use `--keep-csv` para preservar os arquivos.
   * Scripts Standalone: **Mantêm por padrão**. Use `--delete-csv` para deletar os arquivos.
4. **Downloads de CSV**: Recomenda-se realizar localmente ou por GitHub Actions. Servidores VPS comuns costumam ter seus blocos de IPs bloqueados pelo site da Caixa (Erro 403).

---

## 🔌 API Endpoints (Django)

- `GET /api/stats` — Estatísticas gerais.
- `GET /api/filters` — Opções dinâmicas para filtros (estados, tipos, etc).
- `GET /api/cidades/?uf=SP` — Listagem de cidades por UF.
- `GET /api/bairros/?uf=SP&cidade=Sao+Paulo` — Bairros por cidade e estado.
- `GET /api/stats/filtered` — Médias e medianas filtradas.
- `GET /api/properties` — Listagem paginada de imóveis.
