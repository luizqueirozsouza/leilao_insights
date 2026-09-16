# Pipeline CI/CD: teste + deploy do backend no EasyPanel

**Data:** 2026-09-16
**Status:** Aprovado pelo usuário
**Escopo:** Backend Django/Docker. Frontend fica fora (Cloudflare Pages já é automático).

## Contexto

O backend (Django 6 + ASGI/uvicorn, container Docker) é deployado manualmente no
painel do EasyPanel. O frontend estático já é deployado automaticamente pelo
Cloudflare Pages a cada push na main. O objetivo é automatizar o deploy do
backend de forma segura: a cada push na main, rodar os testes existentes e, se
passarem, disparar o deploy no EasyPanel e aplicar migrations.

O projeto já possui um pipeline de dados separado (`.github/workflows/daily-sync.yml`)
que extrai CSVs da Caixa no runner do GitHub e ingere na VPS. Ele **não será
alterado** por este pipeline.

## Gatilho e fluxo

```
push na main
   │
   ▼
Job 1: test  (roda em push na main e em pull_request para main)
  • uv sync --locked
  • uv run python -m unittest discover tests -v
  • smoke: imports dos módulos do pipeline (extrai, enriquece, ingest_dlt, run_daily_pipeline)
  │ sucesso (push na main)
  ▼
Job 2: deploy  (needs: test, apenas push na main)
  • POST na DEPLOY_TRIGGER_URL (EasyPanel: git pull + docker build + deploy)
  • espera ~90s (build no EasyPanel)
  • SSH na VPS → docker exec no container backend → manage.py migrate
  • health check GET /api/stats → espera HTTP 200
```

## Componentes

### Workflow novo: `.github/workflows/backend-ci-cd.yml`

Job `test`:
- `actions/checkout@v4`
- `astral-sh/setup-uv@v5`
- `uv sync --locked`
- `uv run python -m unittest discover tests -v`
- smoke de imports: `python -c "import pipeline.extrai, pipeline.enriquece, pipeline.ingest_dlt, pipeline.run_daily_pipeline"`

Job `deploy` (needs: test, `if: github.ref == 'refs/heads/main'`):
- `curl -X POST "$DEPLOY_TRIGGER_URL"` (secret do environment `production`)
- `sleep 90` (build assíncrono no EasyPanel)
- SSH na VPS com `VPS_SSH_KEY`, `VPS_HOST`, `VPS_USER`, `VPS_PORT`:
  - localizar container `projetos_leilao_insights-backend-*` via `docker ps`
  - `docker exec <container> sh -lc 'cd /app && uv run python backend_django/manage.py migrate'`
- health check: `GET https://api-leilao.kb4x5f.easypanel.host/api/stats` até HTTP 200 (com timeout)
  - O domínio fica hardcoded no workflow; se a API mudar de domínio, atualizar no
    workflow ou mover para um secret opcional `API_HEALTH_URL`.

### Secrets necessários (environment `production`)

- `DEPLOY_TRIGGER_URL` — já criado pelo usuário
- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT` — já existentes
- Opcional: `API_HEALTH_URL` (domínio da API para health check; default hardcoded)

## Decisões

1. **Build fica no EasyPanel**, não é duplicado no runner. O trigger URL já faz
   `git pull` + `docker build` + deploy.
2. **Migrate roda via SSH após o deploy**, porque o CMD do container não roda
   migrate no boot. Isso garante que a migration é aplicada depois que a nova
   versão está no ar. (Alternativa descartada: mudar o Dockerfile para rodar
   migrate no start — não queremos alterar o comportamento do container agora.)
3. **Sem build de imagem nem push para registry** — YAGNI, o EasyPanel builda.
4. **Sem staging** — deploy direto em produção após testes (padrão atual do projeto).
5. **Sem rollback automático** — se o deploy falhar, o workflow fica vermelho e
   notifica; o EasyPanel mantém o estado atual.
6. **Frontend fora do escopo** — já é automático no Cloudflare Pages.

## Tratamento de erro

- Teste falha → job `deploy` não roda; PR/push fica com check vermelho.
- Trigger do EasyPanel falha (HTTP != 200/201/202) → workflow falha.
- Migrate falha → workflow falha com log do comando.
- Health check não responde 200 em até N tentativas → workflow falha (deploy pode
  ter acontecido, mas a API não está saudável — requer inspeção manual).

## Notificação

Sem notificação Telegram no pipeline backend por ora (o pipeline de dados já
notifica; o backend deploy falho aparece como check vermelho no GitHub).
Opção futura: reutilizar `pipeline.notify_telegram` se desejado.

## Fora de escopo (explicitamente não incluído)

- Alterar `daily-sync.yml` ou o cron da VPS.
- Testes de API Django completos (nível mínimo escolhido: testes existentes + imports).
- Lint/typecheck (não configurado no projeto).
- Deploy do frontend (já automático).

## Plano de migração/verificação

1. Criar `.github/workflows/backend-ci-cd.yml`.
2. Validar sintaxe YAML e que os secrets estão acessíveis no environment `production`.
3. Disparar o workflow manualmente (ou fazer um push/PR de teste) e confirmar:
   - testes passam;
   - deploy dispara no EasyPanel;
   - migrate roda no container;
   - `/api/stats` responde 200.
4. Se algo falhar, corrigir o workflow e repetir.

Rollback: remover/desabilitar o workflow `.github/workflows/backend-ci-cd.yml`.
Não há mudança de schema nem de código do backend neste escopo.