# Liberar Acesso + Alertas por Email via Resend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Liberar a listagem completa de leilões para qualquer visitante, permitir alertas para qualquer usuário logado, remover o canal Telegram e enviar alertas por email via Resend com HTML estruturado.

**Architecture:** Três frentes coordenadas: (1) backend de acesso — `access.py`/`views.py`/`auth_views.py` param de restringir por assinatura; (2) backend de notificação — `models.py` remove telegram (migration 0007), `notifiers.py` ganha `ResendNotifier`, `notify_subscribers.py` monta HTML via template; (3) frontend — remove banner demo, gate de assinatura e campos telegram.

**Tech Stack:** Django 6 (PostgreSQL), SDK `resend` (2.46.0, PyPI), Django template engine, uvicorn/EasyPanel, GitHub Actions (backend-ci-cd já existente).

**Spec:** `docs/superpowers/specs/2026-09-17-alerta-email-resend-design.md`

## Global Constraints

- O modelo `Assinatura` permanece no banco; **não** é removido nem destrutivo.
- Migration nova é `auctions.0007_preferenciaalerta_remove_canal_telegram` (RemoveField de `canal_telegram` e `contato_telegram`). Base: `0006_preferenciaalerta_telegram`.
- `ResendNotifier.enviar(destinatario, assunto, html)` — assinatura compatível com o uso atual em `notify_subscribers`.
- `RESEND_API_KEY` lida do ambiente; ausente em dev ⇒ loga e retorna `False` (não envia).
- `RESEND_FROM_EMAIL` default: `"Leilão Insights <onboarding@resend.dev>"`.
- `manage.py` path: `backend_django/manage.py`. Testes: `uv run python -m unittest discover tests -v` (mais os testes Django em `backend_django/auctions/tests.py`).
- Não mexer no `.env` da VPS sem confirmação do usuário.
- Não alterar `run_daily_pipeline.py`, o cron, nem `daily-sync.yml`.
- Usar `render_to_string` do Django para o template `backend_django/templates/emails/alerta_imoveis.html`.

---

### Task 1: Backend — liberar acesso (remover restrição de demo/assinatura)

**Files:**
- Modify: `backend_django/auctions/access.py`
- Modify: `backend_django/auctions/views.py`
- Modify: `backend_django/auctions/auth_views.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `aplicar_modo_demo(qs, request)` retorna `(qs, False)` sempre (queryset intacto); `ver_amostra(request)` retorna `False` sempre; `usuario_tem_assinatura_ativa(user)` mantém assinatura (não-restritiva). `api_preferencias`/`api_preferencias_id` exigem `is_authenticated` mas NÃO exigem assinatura.

- [ ] **Step 1: Alterar `access.py`**

Substitua o corpo das funções de restrição para não filtrar:

```python
def ver_amostra(request) -> bool:
    return False


def _amostra_queryset():
    return []


def aplicar_modo_demo(qs, request):
    """Acesso liberado para todos (sem modo demo). Retorna (queryset, em_demo)."""
    return qs, False
```

Mantenha `usuario_tem_assinatura_ativa`, `UFS_DEMO`, `LIMITE_DEMO`, `POR_UF_DEMO` como estão (não usados, mas sem migration destrutiva).

- [ ] **Step 2: Alterar `views.py`**

- Linha 86: remover a linha `access_scope = 'demo' if request is not None and ver_amostra(request) else 'full'` e trocar por `access_scope = 'full'`.
- Linha 89-90: remover o bloco `if request is not None: base_qs, _ = aplicar_modo_demo(base_qs, request)`.
- Linha 221: trocar `auctions, em_demo = aplicar_modo_demo(auctions, request)` por `em_demo = False`.
- Linha 280: trocar `qs, _ = aplicar_modo_demo(qs, request)` por `pass` (mantém `qs`).
- Linha 294: idem.
- Linha 303: trocar `base_qs, em_demo = aplicar_modo_demo(base_qs, request)` por `em_demo = False`.
- Linha 345: trocar `qs, _ = aplicar_modo_demo(qs, request)` por `pass`.
- Linha 367: trocar `qs, em_demo = aplicar_modo_demo(qs, request)` por `em_demo = False`.
- Linha 11: atualizar o import para remover `ver_amostra` e `aplicar_modo_demo` (manter `usuario_tem_assinatura_ativa`).

Import final: `from .access import usuario_tem_assinatura_ativa`

- [ ] **Step 3: Alterar `auth_views.py`**

- Linhas 257-258 (em `api_preferencias`) e 289-290 (em `api_preferencias_id`): remover o bloco:

```python
    if not usuario_tem_assinatura_ativa(user):
        return JsonResponse({'error': 'Alertas exigem assinatura ativa'}, status=403)
```

- Linha 11: remover `usuario_tem_assinatura_ativa` do import (ficar `from backend_django.auctions.access import ...` vazio ou remover a linha). Como `api_admin_*` ainda pode usar, verificar: `api_admin_subscription` gerencia assinatura (não depende de `usuario_tem_assinatura_ativa`). Remova o import.

- [ ] **Step 4: Rodar os testes Django existentes**

Run: `uv run python backend_django/manage.py test auctions --verbosity 2 2>&1`
Expected: testes existentes passam (o arquivo `auctions/tests.py` pode estar vazio — validar que não há erro de import).

- [ ] **Step 5: Commit**

```bash
git add backend_django/auctions/access.py backend_django/auctions/views.py backend_django/auctions/auth_views.py
git commit -m "feat: libera acesso a listagem e alertas sem assinatura"
```

---

### Task 2: Backend — remover campos Telegram e criar migration 0007

**Files:**
- Modify: `backend_django/auctions/models.py`
- Create: `backend_django/auctions/migrations/0007_preferenciaalerta_remove_canal_telegram.py`
- Modify: `backend_django/auctions/admin.py`

**Interfaces:**
- Consumes: modelo `PreferenciaAlerta` (Task-independent).
- Produces: `PreferenciaAlerta` sem `canal_telegram`/`contato_telegram`; migration `0007` (RemoveField x2). `admin.py` deixa de referenciar `canal_telegram`.

- [ ] **Step 1: Remover campos do modelo**

Em `models.py` linhas 107-108, remover:

```python
    canal_telegram = models.BooleanField(default=False, verbose_name="Notificar por Telegram")
    contato_telegram = models.CharField(max_length=100, blank=True, default='', verbose_name="Telegram (chat ID)")
```

Fica apenas `canal_email = models.BooleanField(default=True, ...)`.

- [ ] **Step 2: Criar a migration**

Crie `backend_django/auctions/migrations/0007_preferenciaalerta_remove_canal_telegram.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auctions', '0006_preferenciaalerta_telegram'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preferenciaalerta',
            name='canal_telegram',
        ),
        migrations.RemoveField(
            model_name='preferenciaalerta',
            name='contato_telegram',
        ),
    ]
```

- [ ] **Step 3: Atualizar `admin.py`**

Linha 46: `list_display = ('usuario', 'uf', 'canal_email', 'criada_em')`
Linha 47: `list_filter = ('uf', 'canal_email')`

- [ ] **Step 4: Aplicar a migration e validar**

Run: `uv run python backend_django/manage.py makemigrations --check --dry-run 2>&1`
Expected: "No changes detected" (ou que apenas `0007` já existe e nada pendente).
Run: `uv run python backend_django/manage.py showmigrations auctions 2>&1 | tail -3`
Expected: `0007_preferenciaalerta_remove_canal_telegram` listado (não aplicado ainda em dev local; será aplicado no deploy).

- [ ] **Step 5: Commit**

```bash
git add backend_django/auctions/models.py backend_django/auctions/migrations/0007_preferenciaalerta_remove_canal_telegram.py backend_django/auctions/admin.py
git commit -m "feat: remove canal telegram das preferencias de alerta (migration 0007)"
```

---

### Task 3: Backend — ResendNotifier + template HTML

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend_django/auctions/notifiers.py`
- Modify: `backend_django/core/settings.py`
- Create: `backend_django/templates/emails/alerta_imoveis.html`
- Modify: `backend_django/auctions/management/commands/test_notifications.py`

**Interfaces:**
- Consumes: `RESEND_API_KEY`, `RESEND_FROM_EMAIL` env vars.
- Produces: `ResendNotifier.enviar(destinatario: str, assunto: str, mensagem: str) -> bool` (mensagem = HTML); `EmailNotifier` mantido como fallback dev; template renderiza com contexto `{assunto, eventos: [{titulo, linha, imovel, uf, cidade, bairro, modalidade, tipo, preco, link}]}`.

- [ ] **Step 1: Adicionar dependência**

Run: `uv add resend` (instala `resend==2.46.0` e atualiza `pyproject.toml` + `uv.lock`).

- [ ] **Step 2: Adicionar `RESEND_FROM_EMAIL` no settings.py**

Após a linha 125 (`DEFAULT_FROM_EMAIL`), adicionar:

```python
RESEND_FROM_EMAIL = env('RESEND_FROM_EMAIL', default='Leilão Insights <onboarding@resend.dev>')
```

- [ ] **Step 3: Adicionar `ResendNotifier` em notifiers.py**

Adicionar ao final do arquivo (mantendo `EmailNotifier` e removendo `TelegramNotifier` e `obter_notifiers`):

```python
class ResendNotifier(Notifier):
    nome = "resend"

    def __init__(self):
        import os
        self.api_key = os.getenv("RESEND_API_KEY", "").strip()
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "Leilão Insights <onboarding@resend.dev>")

    @property
    def disponivel(self) -> bool:
        return bool(self.api_key)

    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> bool:
        if not self.disponivel:
            logger.info("Resend nao configurado (RESEND_API_KEY ausente); pulando envio.")
            return False
        try:
            import resend
            resend.api_key = self.api_key
            resend.Emails.send({
                "from": self.from_email,
                "to": [destinatario],
                "subject": assunto,
                "html": mensagem,
            })
            return True
        except Exception:
            logger.exception("Falha ao enviar e-mail via Resend para %s", destinatario)
            return False
```

Remova a classe `TelegramNotifier` inteira e a função `obter_notifiers`.

- [ ] **Step 4: Criar o template HTML**

Crie `backend_django/templates/emails/alerta_imoveis.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{{ assunto }}</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:8px;overflow:hidden;">
        <tr>
          <td style="background:#0f3d5f;padding:20px 24px;color:#ffffff;">
            <h1 style="margin:0;font-size:20px;">Leilão Insights</h1>
            <p style="margin:4px 0 0;font-size:13px;opacity:.85;">Alertas de leilões da Caixa</p>
          </td>
        </tr>
        <tr><td style="padding:24px;">
          <p style="margin:0 0 16px;font-size:14px;color:#333;">Olá! {{ eventos|length }} evento(s) correspondem aos seus filtros:</p>
          {% for e in eventos %}
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:6px;margin-bottom:16px;">
            <tr>
              <td style="padding:12px 16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;">
                <strong style="color:#0f3d5f;font-size:14px;">{{ e.titulo }}</strong>
                <span style="color:#666;font-size:13px;">&nbsp;·&nbsp;{{ e.uf }}/{{ e.numero_imovel }}</span>
              </td>
            </tr>
            <tr><td style="padding:12px 16px;font-size:13px;color:#333;">
              {% if e.cidade %}<div><strong>Cidade:</strong> {{ e.cidade }}</div>{% endif %}
              {% if e.bairro %}<div><strong>Bairro:</strong> {{ e.bairro }}</div>{% endif %}
              {% if e.modalidade %}<div><strong>Modalidade:</strong> {{ e.modalidade }}</div>{% endif %}
              {% if e.tipo %}<div><strong>Tipo:</strong> {{ e.tipo }}</div>{% endif %}
              {% if e.preco %}<div><strong>Preço:</strong> R$ {{ e.preco }}</div>{% endif %}
              {% if e.link %}<div style="margin-top:8px;"><a href="{{ e.link }}" style="color:#0f3d5f;">Ver detalhes no site da Caixa</a></div>{% endif %}
            </td></tr>
          </table>
          {% endfor %}
          <p style="margin:16px 0 0;font-size:12px;color:#999;">Você está recebendo este e-mail porque criou um alerta no Leilão Insights. Gerencie seus alertas a qualquer momento.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
```

- [ ] **Step 5: Atualizar `test_notifications.py`**

- Linha 5: `from backend_django.auctions.notifiers import EmailNotifier, ResendNotifier`
- Remover toda a lógica de `telegram_requested`, `chat_id`, `--telegram`, `--to`, e o bloco `if telegram_requested:`.
- Adicionar flag `--resend` que envia via `ResendNotifier()` com o `message` como HTML. Exigir `--email` ou `--resend`.
- Mensagem padrão vira HTML simples: `"<p>Esta e uma mensagem de teste do Leilao Insights.</p>"`.

- [ ] **Step 6: Rodar testes de import e lint**

Run: `uv run python -c "import backend_django.auctions.notifiers" 2>&1`
Expected: sem erro.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock backend_django/auctions/notifiers.py backend_django/core/settings.py backend_django/templates/emails/alerta_imoveis.html backend_django/auctions/management/commands/test_notifications.py
git commit -m "feat: envia alertas por email via Resend com template HTML"
```

---

### Task 4: Backend — notify_subscribers gera HTML e envia via Resend

**Files:**
- Modify: `backend_django/auctions/management/commands/notify_subscribers.py`

**Interfaces:**
- Consumes: `ResendNotifier` (Task 3), template `alerta_imoveis.html`, `render_to_string`.
- Produces: comando envia 1 email HTML por preferência com os eventos do dia que batem com os filtros; remove telegram.

- [ ] **Step 1: Ajustar imports e remover telegram**

- Remover `TelegramNotifier` do import; adicionar `ResendNotifier`.
- Adicionar `from django.template.loader import render_to_string`.
- Remover `telegram = TelegramNotifier()` e `canais_ok` com "telegram".

- [ ] **Step 2: Agrupar eventos por preferência e montar HTML**

Reescreva o `handle` para:
1. Coletar eventos (mantém a query SQL atual).
2. Para cada `pref`, coletar a lista de eventos que batem (`_pref_casa`/`_pref_payload_casa`).
3. Para cada evento, montar um dict `{titulo, numero_imovel, uf, cidade, bairro, modalidade, tipo, preco, link}` via `_montar_evento_html(evento, imovel, payload)`.
4. Renderizar `render_to_string("emails/alerta_imoveis.html", {"assunto": assunto, "eventos": lista})`.
5. Se a lista não estiver vazia, `ResendNotifier().enviar(pref.usuario.email, assunto, html)`.
6. Registrar `NotificacaoEnviada` por evento (mesma lógica dedupe atual).

Adicione a função:

```python
def _montar_evento_html(evento: dict, imovel: Auction | None, payload: dict | None = None) -> dict:
    base = _descrever_evento(evento["tipo_evento"])
    dados = {
        "titulo": base,
        "numero_imovel": evento["numero_imovel"],
        "uf": evento["uf"],
        "cidade": None,
        "bairro": None,
        "modalidade": None,
        "tipo": None,
        "preco": None,
        "link": None,
    }
    if imovel:
        dados.update({
            "cidade": imovel.cidade,
            "bairro": imovel.bairro,
            "modalidade": imovel.modalidade,
            "tipo": imovel.tipo_imovel,
            "preco": imovel.preco,
            "link": imovel.link,
        })
    elif payload:
        dados["cidade"] = _payload_value(payload, "Cidade") or None
        dados["bairro"] = _payload_value(payload, "Bairro") or None
        dados["modalidade"] = _payload_value(payload, "Modalidade de venda") or None
        dados["tipo"] = _payload_value(payload, "tipo_imovel", "Tipo de imóvel", "Tipo de imovel") or None
        dados["preco"] = _payload_value(payload, "Preço", "Pre\u00e7o") or None
        dados["link"] = _payload_value(payload, "Link de acesso") or None
    return dados
```

A assinatura do assunto: `f"Alerta de leilão — {dt}"`.

- [ ] **Step 3: Validar com dry-run**

Run: `uv run python backend_django/manage.py notify_subscribers --date 2026-09-16 --dry-run --show-message 2>&1 | head -60`
Expected: lista de envios por email; sem referência a telegram.

- [ ] **Step 4: Commit**

```bash
git add backend_django/auctions/management/commands/notify_subscribers.py
git commit -m "feat: notify_subscribers envia email HTML via Resend"
```

---

### Task 5: Frontend — remover demo/assinatura e campos telegram

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`

**Interfaces:**
- Consumes: API `/me` (que não retorna mais `canal_telegram`/`contato_telegram` após Task 1/2), `/preferencias` (POST/PUT sem telegram).
- Produces: frontend sem banner demo, sem gate de assinatura, sem referências a telegram; listagem visível a todos; botão "Meus alertas" visível apenas logado.

- [ ] **Step 1: Editar `index.html`**

- Linha 61-65: remover o bloco `<div class="demo-banner" id="demo-banner" ...>...</div>` inteiro.
- Linha 187: trocar `Assinatura ativa e necessaria para acesso completo e alertas.` por `Faça login para gerenciar seus alertas.`
- Linha 212-217: remover a seção `Assinatura` do user panel (o `<div class="user-section-head"><h3>Assinatura</h3>...` e os itens `user-subscription-start/end` e `user-subscription-note`). Manter a seção Alertas.
- Linha 285: trocar o texto do modal-sub para `Receba um e-mail diário quando houver imóveis novos, removidos ou alterados que correspondam aos seus filtros.`
- Linha 316-320: remover o `<label class="channel"><input type="checkbox" id="alert-telegram" /> Telegram</label>` e o `<label class="auth-field telegram-field">...<input id="alert-telegram-id" .../></label>`.

- [ ] **Step 2: Editar `app.js` — remover refs demo/telegram/assinatura**

- Linha 55-57: remover `demoBanner`, `demoText`, `demoCta` dos `els`.
- Linha 122-123: remover `alertTelegram`, `alertTelegramId` dos `els`.
- Linha 489: remover a chamada `renderDemoBanner(stats.em_demo);`.
- Linha 512: `isAssinante()` → retornar `true` (ou remover função e trocar chamadas). Mais simples: manter a função mas `return true`. Melhor: remover os gates. Troque os usos: linha 521-525 (renderDemoBanner) — remover; linha 541 (`els.alertasBtn.hidden = true;`) e 546 (`els.alertasBtn.hidden = !isAssinante();`) → `els.alertasBtn.hidden = !authenticated;`.
- Linha 565-581 (`renderUserPanel`): remover as linhas de assinatura (subscription status/start/end/note). Manter nome/email/avatar e a seção de alertas. O botão `userAlertsButton.disabled` → sempre `false` (usuario logado). `userAlertsButton.textContent` → "Gerenciar alertas".
- Linha 629: `const channels = [alert.canal_email ? "E-mail" : null, alert.canal_telegram ? "Telegram" : null].filter(Boolean);` → `const channels = [alert.canal_email !== false ? "E-mail" : null].filter(Boolean);`
- Linha 870-873 (`renderAlertas`): `canais` → só email; remover `if (pref.canal_telegram) canais.push("Telegram");`
- Linha 900-902 (`openAlertas`): remover `els.alertTelegram.checked = false;` e `els.alertTelegramId.value = "";`
- Linha 923-925 (`handleAlertSubmit`): remover `canal_telegram` e `contato_telegram` do body.

- [ ] **Step 3: Validar sintaxe JS**

Run: `node --check frontend/app.js 2>&1`
Expected: sem erro (se `node` disponível). Senão, validar visualmente.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/app.js
git commit -m "feat: remove demo/assinatura e telegram do frontend"
```

---

### Task 6: Testes e validação integrada

**Files:**
- Modify: `tests/test_pipeline_csv_validation.py` (sem mudança necessária — validação)
- Create: `backend_django/auctions/tests.py` (adicionar testes se vazio)

**Interfaces:**
- Consumes: mudanças das Tasks 1-5.
- Produces: evidência de que o conjunto continua passando e o fluxo de alerta HTML gera o conteúdo esperado.

- [ ] **Step 1: Adicionar teste do template HTML**

Em `backend_django/auctions/tests.py`, adicionar:

```python
from django.test import TestCase
from django.template.loader import render_to_string


class EmailTemplateTests(TestCase):
    def test_alerta_imoveis_renders_events(self):
        html = render_to_string("emails/alerta_imoveis.html", {
            "assunto": "Alerta de leilão — 2026-09-16",
            "eventos": [
                {"titulo": "Novo imóvel adicionado", "numero_imovel": "123", "uf": "SP",
                 "cidade": "São Paulo", "bairro": "Centro", "modalidade": "Leilão",
                 "tipo": "Apartamento", "preco": "100000.00", "link": "https://exemplo.com"},
            ],
        })
        self.assertIn("Novo imóvel adicionado", html)
        self.assertIn("123", html)
        self.assertIn("São Paulo", html)
```

- [ ] **Step 2: Rodar todos os testes**

Run: `uv run python -m unittest discover tests -v 2>&1`
Expected: suíte existente passa (6 testes).
Run: `uv run python backend_django/manage.py test auctions --verbosity 2 2>&1`
Expected: `EmailTemplateTests` passa.

- [ ] **Step 3: Smoke de imports do pipeline + backend**

Run: `uv run python -c "import pipeline.extrai, pipeline.enriquece, pipeline.ingest_dlt, pipeline.run_daily_pipeline, backend_django.auctions.notifiers, backend_django.auctions.models, backend_django.auctions.views, backend_django.auctions.auth_views" 2>&1`
Expected: sem erro.

- [ ] **Step 4: Commit**

```bash
git add backend_django/auctions/tests.py
git commit -m "test: cobertura do template de alerta por email"
```

---

### Task 7: Deploy e configuração do Resend na VPS

**Files:**
- Modify: nenhum no repo (configuração de ambiente).
- Action: adicionar env vars no EasyPanel + deploy.

**Interfaces:**
- Consumes: `RESEND_API_KEY` (secret GitHub já criado), `RESEND_FROM_EMAIL`.
- Produces: container da VPS com `RESEND_API_KEY`/`RESEND_FROM_EMAIL` setadas; migration `0007` aplicada; `notify_subscribers` envia email real.

- [ ] **Step 1: Push da branch para o GitHub**

Run: `git push`
Expected: push ok; `backend-ci-cd` roda testes.

- [ ] **Step 2: Adicionar env vars no EasyPanel (com confirmação do usuário)**

No painel EasyPanel → serviço backend → Environment, adicionar:
- `RESEND_API_KEY=re_...`
- `RESEND_FROM_EMAIL="Leilão Insights <onboarding@resend.dev>"`

Confirmar com o usuário antes de aplicar.

- [ ] **Step 3: Deploy**

O `backend-ci-cd` já deploya na VPS. Após o deploy, validar:

Run (via SSH):
```bash
docker exec projetos_leilao_insights-backend-1 sh -lc 'cd /app && uv run python backend_django/manage.py showmigrations auctions | tail -3'
```
Expected: `0007` aplicado (`[X]`).

- [ ] **Step 4: Validar envio real**

Run (via SSH):
```bash
docker exec projetos_leilao_insights-backend-1 sh -lc 'cd /app && uv run python backend_django/manage.py test_notifications --resend --email delivered@resend.dev'
```
Expected: `[OK] Resend -> delivered@resend.dev` e email visível no dashboard do Resend (tab Emails).

- [ ] **Step 5: Validação final de acesso**

Abrir a URL pública da API e confirmar que `/api/stats` retorna o total completo (sem `em_demo` restrito):
```bash
curl -s https://api-leilao.kb4x5f.easypanel.host/api/stats
```
Expected: `total` com o acervo completo (não 30).