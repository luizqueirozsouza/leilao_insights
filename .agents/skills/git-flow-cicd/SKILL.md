---
name: git-flow-cicd
description: Orquestra o fluxo de entrega do projeto Leilão Insights — criar branch de trabalho, commitar, abrir PR, acompanhar o CI/CD (job Test) e o deploy automático no EasyPanel via GitHub Actions. Use sempre que o usuário pedir para "enviar/enviar para o GitHub", "subir/criar branch", "abrir PR/pull request", "commitar e pushar", "deployar", "acompanhar o CI/CD", "validar o deploy", "fazer rollback", ou quando ele terminar uma mudança e quiser publicá-la. Também use ao diagnosticar por que um PR/check/deploy falhou ou não disparou.
---

# Git Flow + CI/CD do Leilão Insights

Esta skill padroniza como o código vai da sua máquina até produção, respeitando a
proteção de branch e o pipeline automático já configurados no GitHub.

## Modelo de entrega (GitHub Flow)

```
feat/x ── c1 ── c2 ── c3 ──┐  (branch: vários commits)
main   ─────────────────────┴──► [PR] ─► CI roda TESTE ─► verde ─► auto-merge
                                                   │
                                                   ▼
                             push em main ─► CI roda TESTE + DEPLOY ─► EasyPanel
```

- Nenhum commit vai **direto** para `main`. Tudo passa por branch + PR.
- O job `deploy` do workflow `backend-ci-cd.yml` só roda em `main`
  (`if: github.ref == 'refs/heads/main'`). PR roda apenas o job `Test`.
- A branch protection de `main` exige: PR + 1 review + check `Test` verde.
  Auto-merge está habilitado: quando o CI passa, o PR é mergeado sozinho e a
  branch é deletada. Force push em `main` é bloqueado.

## Configuração vigente (não reconfigurar sem necessidade)

| Item | Valor |
|------|-------|
| Workflow CI/CD | `.github/workflows/backend-ci-cd.yml` |
| Check obrigatório em `main` | `Test` |
| Deploy | POST na `DEPLOY_TRIGGER_URL` (secret do env `production`) + SSH migrate + health check `/api/stats` |
| Secrets | `DEPLOY_TRIGGER_URL`, `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT`, `RESEND_API_KEY` (env `production`) |
| Testes | `uv run python -m unittest discover tests -v` + smoke de imports |
| Repo | `luizqueirozsouza/leilao_insights` (branch padrão `main`) |

## Rito de entrega (o que fazer quando o usuário diz "envia/enviar pro GitHub")

Siga esta ordem. Use o `gh` CLI. Trabalhe na branch certa.

### 1. Estado do repositório

Antes de tudo:

```bash
git fetch origin
git status --short
git branch --show-current
git log --oneline origin/main..HEAD   # commits ainda não mergeados
```

Regras:
- Se você está em `main` com commits locais: **não** push direto. Crie uma branch
  (`git switch -c feat/...`) e leve os commits para ela.
- Se o remote avançou (`git rev-list --count HEAD..origin/main` > 0), faça
  `git rebase origin/main` antes de continuar.
- Nunca use force push.

### 2. Branch

Nomeie por tipo: `feat/...`, `fix/...`, `chore/...`, `docs/...`, `test/...`,
`ci/...`. Exemplos: `feat/alerta-resend`, `fix/cron-fuso`, `ci/deploy-backend`.

```bash
git switch -c feat/descricao
```

Se já existem commits soltos na branch, os múltiplos commits são **ok** — não há
necessidade de squash. O PR pode conter vários commits.

### 3. Commit

Estage apenas o que pertence à mudança (nunca `git add .` cego — respeite o
`.gitignore` e não commite secrets, `.env`, `data/`).

```bash
git add <arquivos>
git commit -m "<tipo>: <descricao curta>"
```

Estilo de mensagem do projeto (ver `git log --oneline`):
`fix:`, `feat:`, `chore:`, `docs:`, `test:`, `ci:` em minúsculo, seguido de
descrição em português. Ex.: `feat: envia alertas por email via Resend`.

### 4. Push

```bash
git push -u origin HEAD
```

### 5. PR

```bash
gh pr create --base main --head "$(git branch --show-current)" \
  --title "<tipo>: <descricao>" --body "<o que muda e por quê>"
```

O body deve explicar o quê, o porquê e como foi validado (testes rodados,
deploy testado, etc.).

### 6. Acompanhar o CI/CD (PR)

O auto-merge exige que o check `Test` fique verde. Acompanhe:

```bash
gh pr checks <branch> --watch
# ou
gh run list --workflow=backend-ci-cd.yml --limit 3
```

- **Verde**: o auto-merge mergeia sozinho. Depois do merge, o push em `main`
  dispara o deploy automaticamente.
- **Falha**: investigue antes de qualquer retry. Leia o log do job `Test`:
  `gh run view <run-id> --log-failed`. Corrija na branch e faça `git push`
  (novo commit). Não force, não feche o PR sem resolver.

### 7. Validar o deploy (pós-merge)

Depois do auto-merge, o deploy roda em `main`. Acompanhe a run:

```bash
gh run list --workflow=backend-ci-cd.yml --limit 1
gh run watch <run-id> --exit-status --interval 20
```

Sucesso = job `Test` verde + job `Deploy to EasyPanel` verde
(trigger HTTP 200, migrate ok, health check `/api/stats` → 200).

Confirmação adicional na VPS (opcional):

```bash
ssh -i ~/.ssh/github_actions_app_leilao root@38.242.142.197 \
  "cd /etc/easypanel/projects/projetos/leilao_insights/code && git log --oneline -1"
```

O HEAD exibido deve ser o commit mergeado.

### 8. Rollback (se o deploy quebrou produção)

O pipeline atual não tem rollback automático. Se necessário:

1. Reverta o commit na `main` (NUNCA force push):
   ```bash
   git switch main && git pull
   git revert <sha-do-commit-ruim>
   git push
   ```
2. O push do revert dispara novo deploy automaticamente.
3. Acompanhe o deploy como no passo 7.

## Diagnóstico rápido (quando algo não disparou ou falhou)

| Sintoma | Provável causa | Ação |
|---------|----------------|------|
| PR sem o check `Test` | Workflow não rodou ou ainda em fila | `gh pr checks <branch> --watch` |
| Check `Test` vermelho | Teste/import quebrou | `gh run view <id> --log-failed` |
| Deploy não rodou pós-merge | Job `deploy` só roda em `main`; PR em branch não deploya | Confirmar que o merge ocorreu em `main` |
| `Missing secret X` | Secret não existe no env `production` | `gh secret list --env production` |
| Run não aparece | Push não atingiu `main` ou workflow desabilitado | `gh workflow list` + `gh run list --limit 5` |

## Lembrete importante

- **Nunca** commit/push direto em `main`.
- **Nunca** force push (`--force`), nem em branch.
- Ao terminar uma entrega, avise o usuário com: SHA mergeado, resultado do
  deploy (ou link da run), e o que validou. Não encha de detalhes — o que
  importa é "subiu, deploy ok".