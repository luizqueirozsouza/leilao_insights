# Leilao Insights

Painel de inteligencia imobiliaria para acompanhar imoveis de leilao da Caixa.

## Arquitetura

Este repositorio usa o GitHub como origem unica para dois deploys:

- `frontend/`: site estatico publicado no Cloudflare Pages.
- `backend_django/`: API JSON, admin, comandos de ingestao e pagina SSR auxiliar na VPS.
- `backend_fastapi/`: servico complementar para futuras rotas analiticas e IA na VPS.
- `extrai.py` e `ingest.py`: pipeline de coleta e carga dos dados.
- `data/`: snapshots locais dos CSVs baixados da Caixa.

Fluxo em producao:

1. Cloudflare Pages publica o conteudo de `frontend/`.
2. O frontend chama a API Django hospedada na VPS.
3. EasyPanel faz deploy do backend a partir do mesmo repositorio no GitHub.
4. PostgreSQL fica na VPS ou em um servico externo.
5. A atualizacao da base roda via comandos Django no container/servico do backend.

## Banco de Dados

Tabelas principais:

- `snapshot_imoveis`: snapshot bruto da carga do dia.
- `current_imoveis`: estado atual usado pela API e pelo painel.
- `changes`: eventos `ENTER`, `EXIT` e `UPDATE`.

## Desenvolvimento Local

Requisitos:

- Python 3.13+
- `uv`
- PostgreSQL

Instale as dependencias:

```bash
uv sync
```

Configure o arquivo `.env` na raiz:

```env
host=localhost
port=5432
database="db_leiloes"
user="postgres"
password="SUA_SENHA"
sslmode="disable"
SECRET_KEY="chave-local"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:5500
```

Rode as migrations:

```bash
uv run python backend_django/manage.py migrate
```

Suba o Django:

```bash
uv run python backend_django/manage.py runserver
```

Suba o FastAPI, se precisar:

```bash
uv run uvicorn backend_fastapi.main:app --host 0.0.0.0 --port 8001
```

Para testar o frontend estatico localmente, abra `frontend/index.html` ou use uma extensao como Live Server. Se usar Live Server, mantenha a origem em `CORS_ALLOWED_ORIGINS`.

## Atualizar a Base

O fluxo completo baixa os CSVs e ingere no banco:

```bash
uv run python backend_django/manage.py sync_auctions --date 2026-04-25 --verbose
```

Por padrao, os comandos Django removem os CSVs do snapshot depois que a ingestao termina com sucesso. Para manter os arquivos para auditoria ou debug, use `--keep-csv`:

```bash
uv run python backend_django/manage.py sync_auctions --date 2026-04-25 --verbose --keep-csv
```

Tambem e possivel rodar em duas etapas:

```bash
uv run python backend_django/manage.py extrai_auctions --date 2026-04-25 --verbose
uv run python backend_django/manage.py ingest_auctions --date 2026-04-25 --verbose
```

Os scripts diretos continuam disponiveis. Neles, a remocao dos CSVs e opcional com `--delete-csv`:

```bash
uv run python extrai.py --date 2026-04-25 --verbose
uv run python ingest.py --date 2026-04-25 --verbose --delete-csv
```

## Deploy do Backend na VPS com EasyPanel

Use o GitHub como origem do app no EasyPanel.

Configuracao sugerida:

- Tipo: Docker app ou Compose app.
- Repositorio: este repositorio no GitHub.
- Branch: `main` ou a branch usada em producao.
- Dockerfile: `Dockerfile`.
- Porta exposta pelo Django: `8000`.

Variaveis de ambiente no EasyPanel:

```env
host=SEU_HOST_POSTGRES
port=5432
database="db_leiloes"
user="postgres"
password="SUA_SENHA"
sslmode="disable"
SECRET_KEY="uma-chave-forte"
DEBUG=False
ALLOWED_HOSTS=api.seu-dominio.com,SEU_IP_DA_VPS
CORS_ALLOWED_ORIGINS=https://seu-projeto.pages.dev,https://www.seu-dominio.com

# Sessao/CSRF para o login cross-origin (SPA no Cloudflare Pages).
# IMPORTANTE: adicione a origem do frontend tambem em CSRF_TRUSTED_ORIGINS,
# senao o login/registro falha por CSRF.
CSRF_TRUSTED_ORIGINS=https://seu-projeto.pages.dev,https://www.seu-dominio.com

# E-mail (SMTP) - usado pelos alertas de assinante por e-mail
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seu-provedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=no-reply@seu-dominio.com
EMAIL_HOST_PASSWORD=SUA_SENHA_SMTP
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Leilao Insights <no-reply@seu-dominio.com>

# WhatsApp (opcional) - usado pelos alertas de assinante via WhatsApp
# Se ausente, o canal WhatsApp fica indisponivel e so o e-mail e usado.
WHATSAPP_TOKEN=SEU_TOKEN
WHATSAPP_PHONE_ID=SEU_PHONE_ID
# WHATSAPP_API_URL= (opcional; default: Graph API v18.0)
```

> Nota: com `DEBUG=False`, os cookies de sessao/CSRF usam `SameSite=None; Secure`, exigindo HTTPS em ambos (API e frontend). Em desenvolvimento local (`DEBUG=True`), o default e `Secure=False`, o que permite testar em `http://localhost`.

Comandos uteis no container do backend:

```bash
uv run python backend_django/manage.py migrate
uv run python backend_django/manage.py sync_auctions --date 2026-04-25 --verbose
```

## Rotina Diaria na VPS (EasyPanel Cron App)

A rotina diaria foi migrada para VPS com orquestracao local:

- `pipeline/run_daily_pipeline.py`: executa `extrai -> ingest_dlt -> Telegram`.
- `pipeline/ingest_dlt.py`: faz a ingestao no PostgreSQL usando DLT + SQL para manter `changes/current_imoveis`.
- `pipeline/notify_telegram.py`: envia resumo de sucesso ou alerta de falha.

### Variaveis de ambiente adicionais

```env
PIPELINE_TZ=America/Sao_Paulo
DLT_PIPELINE_NAME=leilao_snapshot_daily
DLT_DATASET_NAME=public
TELEGRAM_BOT_TOKEN=123456:ABCDEF
TELEGRAM_CHAT_ID=-1001234567890
```

As variaveis de banco (`host`, `port`, `database`, `user`, `password`, `sslmode`) continuam obrigatorias.

### Comando do cron (EasyPanel)

Executar diariamente as 08:00 BRT:

```bash
uv run python pipeline/run_daily_pipeline.py --verbose
```

Para manter os CSVs apos sucesso:

```bash
uv run python pipeline/run_daily_pipeline.py --verbose --keep-csv
```

### Workflow legado (manual)

O workflow `.github/workflows/daily-sync.yml` foi mantido apenas com `workflow_dispatch` para rollback/manual run. O gatilho automatico por `schedule` foi removido.

Se usar `docker-compose.yml`, os servicos previstos sao:

- `backend`: API Django e comandos do projeto na porta `8000`.
- `fastapi`: servico auxiliar na porta `8001`.

## Deploy do Frontend no Cloudflare Pages

Voce pode usar o mesmo repositorio GitHub no Cloudflare Pages.

Configuracao do projeto Pages:

- Framework preset: `None`.
- Build command: deixe vazio.
- Build output directory: `frontend`.
- Root directory: deixe em branco se o Pages permitir escolher output `frontend`; caso contrario, defina `frontend` como root e use output `.`.

Antes do deploy, ajuste `frontend/config.js` para apontar para a API da VPS:

```js
window.LEILAO_CONFIG = {
  API_BASE: "https://api.seu-dominio.com/api"
};
```

Depois de publicar o Pages, copie o dominio gerado, por exemplo:

```text
https://leilao-insights.pages.dev
```

Inclua esse dominio no backend:

```env
CORS_ALLOWED_ORIGINS=https://leilao-insights.pages.dev
```

Se tambem usar dominio proprio no Cloudflare Pages, inclua os dois:

```env
CORS_ALLOWED_ORIGINS=https://leilao-insights.pages.dev,https://www.seu-dominio.com
```

## API Django

- `GET /api/stats`: estatisticas gerais (inclui `em_demo` para indicar modo demonstracao).
- `GET /api/filters`: filtros dinamicos (UF, cidade, bairro, modalidade e tipo de imovel).
- `GET /api/cidades/?uf=SP`: cidades por UF.
- `GET /api/bairros/?uf=SP&cidade=Sao+Paulo`: bairros por UF e cidade.
- `GET /api/stats/filtered`: media e mediana filtradas.
- `GET /api/properties`: lista de imoveis (aceita filtro `tipo=casa|apartamento|terreno`).
- `GET /api/property/<numero_imovel>`: detalhes enriquecidos do imovel, buscados sob demanda na pagina da Caixa e em cache.
- `POST /api/registro`: cria conta (email + senha).
- `POST /api/login`: autentica e inicia sessao.
- `POST /api/logout`: encerra a sessao.
- `GET /api/me`: dados do usuario autenticado (assinatura e preferencias de alerta).
- `GET/POST /api/preferencias`: listar/criar preferencias de alerta (somente assinantes).
- `PUT/DELETE /api/preferencias/<id>`: atualizar/remover preferencia de alerta.

## Modo Demonstracao, Assinaturas e Alertas

Sem login (ou sem assinatura ativa), o painel exibe apenas uma **amostra de demonstracao**
(30 imoveis cobrindo varias UFs), com banner avisando o modo demo. O acesso completo e
liberado apenas para usuarios com **assinatura ativa**.

- A assinatura e ativada/desativada manualmente no Django Admin (modelo `Assinatura`),
  com validade opcional (`data_fim`). Nao ha gateway de pagamento nesta fase.
- **Alertas**: o assinante configura preferencias (UF/cidade/bairro/modalidade) e canais
  (e-mail e/ou WhatsApp). A cada ingestao diaria, os eventos `ENTER`/`EXIT`/`UPDATE` da
  tabela `changes` sao cruzados com as preferencias e notificacoes sao disparadas.
- A entrega usa `backend_django/auctions/notifiers.py` (SMTP para e-mail e interface para
  WhatsApp). Registro em `NotificacaoEnviada` evita envio duplicado na mesma data.

### Comandos novos

- `backfill_tipo_imovel`: preenche `tipo_imovel` dos imoveis existentes.
- `notify_subscribers`: dispara alertas com base nos eventos do dia (`--date`, `--dry-run`).

```bash
uv run python backend_django/manage.py backfill_tipo_imovel
uv run python backend_django/manage.py notify_subscribers --date 2026-04-25 --dry-run
```

O `notify_subscribers` e chamado automaticamente pelo `pipeline/run_daily_pipeline.py`
apos a ingestao.

## Tipo de Imovel e Enriquecimento

- `tipo_imovel` normaliza cada imovel em `apartamento`, `casa`, `terreno` ou `outro`,
  derivado deterministicamente na ingestao e filtrável no painel.
- O endpoint `GET /api/property/<numero>` busca, sob demanda, os dados detalhados da pagina
  da Caixa (area, quartos, matricula, comarca, formas de pagamento e regras do certame),
  guardando o resultado em `dados_enriquecidos` para consultas futuras. O parser esta em
  `backend_django/auctions/caixa_detail.py`.

## Checklist de Producao

- Configurar PostgreSQL e variaveis no EasyPanel.
- Rodar migrations no backend.
- Configurar `ALLOWED_HOSTS` com dominio/API da VPS.
- Configurar `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS` com o dominio do Cloudflare Pages.
- Adicionar `EMAIL_*` (e, se usar, `WHATSAPP_*`) para os alertas de assinante.
- Rodar `backfill_tipo_imovel` para preencher o tipo dos imoveis existentes.
- Ajustar `frontend/config.js` com a URL publica da API.
- Publicar backend no EasyPanel a partir do GitHub.
- Publicar frontend no Cloudflare Pages a partir do mesmo GitHub.
- Rodar `sync_auctions` no backend para carregar a base inicial.
- Ativar assinaturas no Django Admin (modelo `Assinatura`) para liberar acesso completo.
