---
name: git-flow-cicd
description: Orquestra o fluxo de entrega de um projeto — criar branch de trabalho, commitar, abrir PR, acompanhar o CI/CD e o deploy automático via GitHub Actions. Use sempre que o usuário pedir para "enviar/enviar para o GitHub", "subir/criar branch", "abrir PR/pull request", "commitar e pushar", "deployar", "acompanhar o CI/CD", "validar o deploy", "fazer rollback", ou quando ele terminar uma mudança e quiser publicá-la. Também use ao diagnosticar por que um PR/check/deploy falhou ou não disparou.
---

# Git Flow + CI/CD

Esta skill padroniza como o código vai da sua máquina até produção, respeitando a
proteção de branch e o pipeline automático configurados no GitHub.

## Configuração do projeto

**LEIA `config.yml` (mesmo diretório desta skill) ANTES de qualquer ação.** Ele
contém todos os valores específicos do projeto (repo, branch, workflow, secrets,
SSH, health check). Nunca use valores hardcoded desta SKILL.md — o `config.yml`
é a fonte da verdade.

Para usar esta skill em outro projeto: copie a pasta `git-flow-cicd/` para
`.agents/skills/` do outro projeto e edite apenas `config.yml`.

Resumo do fluxo (valores de exemplo — use os do `config.yml`):

```
feat/x ── c1 ── c2 ── c3 ──┐  (branch: vários commits)
<base> ─────────────────────┴──► [PR] ─► CI roda TESTE ─► verde ─► auto-merge
                                                   │
                                                   ▼
                             push em <base> ─► CI roda TESTE + DEPLOY ─► produção
```

- Nenhum commit vai **direto** para a branch base. Tudo passa por branch + PR.
- O job de deploy do workflow só roda na branch base
  (`if: github.ref == 'refs/heads/<base>'`). PR roda apenas o job de teste.
- A branch protection da base exige: PR + review + check obrigatório verde.
  Auto-merge habilitado: CI verde → merge sozinho + branch deletada.
  Force push na base é bloqueado.

## Rito de entrega (quando o usuário diz "envia/enviar pro GitHub")

Siga esta ordem. Use o `gh` CLI. Trabalhe na branch certa.

### 1. Estado do repositório

Antes de tudo:

```bash
git fetch origin
git status --short
git branch --show-current
git log --oneline origin/<base>..HEAD   # commits ainda não mergeados
```

Regras:
- Se você está na branch base com commits locais: **não** push direto. Crie uma
  branch (`git switch -c feat/...`) e leve os commits para ela.
- Se o remote avançou (`git rev-list --count HEAD..origin/<base>` > 0), faça
  `git rebase origin/<base>` antes de continuar.
- Nunca use force push.

### 2. Branch

Nomeie por tipo: `feat/...`, `fix/...`, `chore/...`, `docs/...`, `test/...`,
`ci/...` (prefixos do `config.yml`). Exemplos: `feat/alerta-resend`,
`fix/cron-fuso`, `ci/deploy-backend`.

```bash
git switch -c feat/descricao
```

Múltiplos commits na branch são **ok** — não há necessidade de squash. O PR pode
conter vários commits.

### 3. Commit

Estage apenas o que pertence à mudança (nunca `git add .` cego — respeite o
`.gitignore` e não commite secrets, `.env`, `data/`).

```bash
git add <arquivos>
git commit -m "<tipo>: <descricao curta>"
```

Estilo (ver `git log --oneline`): prefixo em minúsculo (`feat:`, `fix:`,
`chore:`, `docs:`, `test:`, `ci:`) + descrição no idioma do `config.yml`.
Ex.: `feat: envia alertas por email via Resend`.

### 4. Push

```bash
git push -u origin HEAD
```

### 5. PR

```bash
gh pr create --base <base> --head "$(git branch --show-current)" \
  --title "<tipo>: <descricao>" --body "<o que muda e por quê>"
```

O body deve explicar o quê, o porquê e como foi validado (testes rodados,
deploy testado, etc.).

### 6. Acompanhar o CI/CD (PR)

O auto-merge exige que o check obrigatório fique verde. Acompanhe:

```bash
gh pr checks <branch> --watch
# ou
gh run list --workflow=<workflow> --limit 3
```

- **Verde**: o auto-merge mergeia sozinho. Depois do merge, o push na base
  dispara o deploy automaticamente.
- **Falha**: investigue antes de qualquer retry. Leia o log do job de teste:
  `gh run view <run-id> --log-failed`. Corrija na branch e faça `git push`
  (novo commit). Não force, não feche o PR sem resolver.

### 7. Validar o deploy (pós-merge)

Depois do auto-merge, o deploy roda na base. Acompanhe a run:

```bash
gh run list --workflow=<workflow> --limit 1
gh run watch <run-id> --exit-status --interval 20
```

Sucesso = job de teste verde + job de deploy verde
(trigger HTTP 200, migrate ok, health check → 200).

Confirmação adicional no servidor (opcional, usando `config.yml.ssh`):

```bash
ssh -i <ssh.key> <ssh.user>@<ssh.host> \
  "cd <ssh.deploy_dir> && git log --oneline -1"
```

O HEAD exibido deve ser o commit mergeado.

### 8. Rollback (se o deploy quebrou produção)

O pipeline atual não tem rollback automático. Se necessário:

1. Reverta o commit na base (NUNCA force push):
   ```bash
   git switch <base> && git pull
   git revert <sha-do-commit-ruim>
   git push
   ```
2. O push do revert dispara novo deploy automaticamente.
3. Acompanhe o deploy como no passo 7.

## Diagnóstico rápido (quando algo não disparou ou falhou)

| Sintoma | Provável causa | Ação |
|---------|----------------|------|
| PR sem o check obrigatório | Workflow não rodou ou ainda em fila | `gh pr checks <branch> --watch` |
| Check vermelho | Teste/import quebrou | `gh run view <id> --log-failed` |
| Deploy não rodou pós-merge | Job de deploy só roda na base; PR em branch não deploya | Confirmar que o merge ocorreu na base |
| `Missing secret X` | Secret não existe no env `production` | `gh secret list --env production` |
| Run não aparece | Push não atingiu a base ou workflow desabilitado | `gh workflow list` + `gh run list --limit 5` |

## Lembrete importante

- **Nunca** commit/push direto na branch base.
- **Nunca** force push (`--force`), nem em branch.
- Ao terminar uma entrega, avise o usuário com: SHA mergeado, resultado do
  deploy (ou link da run), e o que validou. Não encha de detalhes — o que
  importa é "subiu, deploy ok".