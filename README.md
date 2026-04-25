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
```

Comandos uteis no container do backend:

```bash
uv run python backend_django/manage.py migrate
uv run python backend_django/manage.py sync_auctions --date 2026-04-25 --verbose
```

## Rotina Diaria com GitHub Actions

O repositorio inclui o workflow `.github/workflows/daily-sync.yml`.

Ele pode ser executado de duas formas:

- Automaticamente todos os dias as 08:00 no horario de Sao Paulo.
- Manualmente em `GitHub > Actions > Daily auction sync > Run workflow`.

O GitHub Actions nao roda a ingestao dentro do proprio GitHub. Ele acessa a VPS por SSH e executa o comando de atualizacao la, onde estao o backend, o `.env` e o acesso ao banco.

Configure estes secrets no GitHub em `Settings > Secrets and variables > Actions > New repository secret`:

- `VPS_HOST`: IP ou dominio da VPS.
- `VPS_USER`: usuario SSH da VPS.
- `VPS_PORT`: porta SSH, opcional. Se nao configurar, usa `22`.
- `VPS_SSH_KEY`: chave privada SSH autorizada na VPS.
- `VPS_SYNC_COMMAND`: comando que sera executado na VPS.

Exemplo de `VPS_SYNC_COMMAND` se o projeto estiver direto na VPS:

```bash
cd /caminho/do/app_leilao && uv run python backend_django/manage.py sync_auctions --date $(date +%F) --verbose
```

Exemplo se voce for executar dentro de um container Docker:

```bash
docker exec NOME_DO_CONTAINER uv run python backend_django/manage.py sync_auctions --date $(date +%F) --verbose
```

Exemplo com Docker Compose:

```bash
cd /caminho/do/app_leilao && docker compose exec -T backend uv run python backend_django/manage.py sync_auctions --date $(date +%F) --verbose
```

Para gerar uma chave SSH dedicada para o GitHub Actions:

```bash
ssh-keygen -t ed25519 -C "github-actions-app-leilao" -f ~/.ssh/github_actions_app_leilao
```

Depois, adicione o conteudo de `~/.ssh/github_actions_app_leilao.pub` no arquivo `~/.ssh/authorized_keys` da VPS e salve o conteudo da chave privada `~/.ssh/github_actions_app_leilao` no secret `VPS_SSH_KEY`.

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

- `GET /api/stats`: estatisticas gerais.
- `GET /api/filters`: filtros dinamicos.
- `GET /api/cidades/?uf=SP`: cidades por UF.
- `GET /api/bairros/?uf=SP&cidade=Sao+Paulo`: bairros por UF e cidade.
- `GET /api/stats/filtered`: media e mediana filtradas.
- `GET /api/properties`: lista de imoveis.

## Checklist de Producao

- Configurar PostgreSQL e variaveis no EasyPanel.
- Rodar migrations no backend.
- Configurar `ALLOWED_HOSTS` com dominio/API da VPS.
- Configurar `CORS_ALLOWED_ORIGINS` com o dominio do Cloudflare Pages.
- Ajustar `frontend/config.js` com a URL publica da API.
- Publicar backend no EasyPanel a partir do GitHub.
- Publicar frontend no Cloudflare Pages a partir do mesmo GitHub.
- Rodar `sync_auctions` no backend para carregar a base inicial.
