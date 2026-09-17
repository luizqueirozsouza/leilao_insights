# Liberar acesso + Alertas por Email via Resend

**Data:** 2026-09-17
**Status:** Aprovado pelo usuário (design em 4 seções)
**Escopo:** Listagem liberada sem login; alertas exigem login; remoção do canal Telegram; envio de alertas por email via Resend (SDK Python) com HTML estruturado.

## Contexto

O projeto hoje restringe o acesso ao acervo por assinatura: usuários sem assinatura
ativa veem apenas uma amostra de 30 imóveis de 5 UFs (`aplicar_modo_demo`). Alertas
só podem ser criados por assinantes. O canal de notificação atual é Telegram
(que já substituiu o WhatsApp numa migration anterior) além de um `EmailNotifier`
baseado em `django.core.mail` com backend `console` (não envia de verdade).

O objetivo é: (1) liberar a listagem completa para qualquer visitante, sem login;
(2) permitir que qualquer usuário logado crie alertas de filtros; (3) enviar os
alertas por email usando o Resend como provedor de transação; (4) remover o canal
Telegram de ponta a ponta.

## Decisões

### 1. Liberar listagem sem login; alertas exigem login

- `pipeline`/`access.py`: `aplicar_modo_demo` e `ver_amostra` deixam de restringir.
  O queryset retornado é sempre o completo e `em_demo` é sempre `False`.
- `views.py`: remover as chamadas a `aplicar_modo_demo` (8+ locais), o
  `access_scope='demo'` e a lógica de filtro de amostra. Manter `em_demo: false`
  no payload quando existir, por compatibilidade com o frontend (que deixa de usá-lo).
- `auth_views.py`: `api_preferencias` e `api_preferencias_id` exigem **login**
  (mantêm o check `is_authenticated`) mas removem o check de **assinatura ativa**.
- Frontend: remover `demoBanner`, gate `isAssinante()`, botões/CTA de "Assine",
  textos de assinatura. O botão de alertas fica visível apenas para usuário logado.
- O modelo `Assinatura` permanece no banco (sem migration destrutiva), mas não
  restringe nenhuma rota.

### 2. Remover Telegram de ponta a ponta

- `models.py`: remover `canal_telegram` e `contato_telegram` de `PreferenciaAlerta`
  → nova migration `0007_preferenciaalerta_remove_canal_telegram`.
- `notifiers.py`: remover `TelegramNotifier` e `obter_notifiers`; manter apenas o
  notifier de email.
- `notify_subscribers.py`: remover toda a lógica de Telegram (canais, contato,
  `TelegramNotifier()`); enviar apenas por email.
- `auth_views.py`: `_serializar_preferencia` e o POST/PUT de `api_preferencias`
  removem os campos telegram.
- Frontend: remover `alertTelegram`, `alertTelegramId`, o checkbox "Telegram", o
  input de chat ID e a coluna "Telegram" na listagem de canais. Fica apenas o
  toggle de email (default `true`).
- `.env` da VPS: `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` deixam de ser usados.
  Não serão removidos do `.env` sem confirmação do usuário (ficam inertes).

### 3. Envio por email via Resend (SDK Python) com HTML

- `pyproject.toml`: adicionar dependência `resend`.
- `notifiers.py`: novo `ResendNotifier`:
  - Lê `RESEND_API_KEY` do ambiente.
  - `enviar(destinatario, assunto, html)` → `resend.Emails.send(...)` com
    `from=RESEND_FROM_EMAIL`, `to=[destinatario]`, `subject`, `html`.
  - Se `RESEND_API_KEY` ausente (dev), loga e retorna `False` (não envia).
  - Mantém a assinatura do método `enviar` compatível com `notify_subscribers`.
- `settings.py`: `RESEND_FROM_EMAIL = env('RESEND_FROM_EMAIL', default='Leilão Insights <onboarding@resend.dev>')`.
  O `DEFAULT_FROM_EMAIL` continua existindo como fallback dev (backend console).
- `notify_subscribers.py`: `_montar_mensagem` passa a montar **HTML estruturado**
  (tabela com imóvel, UF, cidade, bairro, modalidade, tipo, preço, link), renderizado
  a partir de template.
- Novo template: `backend_django/templates/emails/alerta_imoveis.html`, renderizado
  com o template engine do Django (`render_to_string`).
- O pipeline diário (`run_daily_pipeline.py`) já chama `notify_subscribers` — sem
  mudança no pipeline; apenas o notifier interno muda.

### 4. Configuração, deploy e validação

- Env vars a adicionar no `.env` da VPS (com confirmação do usuário):
  - `RESEND_API_KEY=re_...`
  - `RESEND_FROM_EMAIL="Leilão Insights <onboarding@resend.dev>"`
- GitHub secret `RESEND_API_KEY` (environment `production`) — já criado pelo usuário.
- Deploy: o backend-ci-cd existente deploya na VPS; após o deploy, adicionar as env
  vars no EasyPanel e redeploy, ou incluir antes.
- Validação:
  - Teste local de `resend.Emails.send` para `delivered@resend.dev` (endereço de
    teste do Resend).
  - `notify_subscribers --dry-run` num dia com eventos para conferir o HTML.
  - Confirmar entrega real no dashboard do Resend (tab Emails).

## Não faz parte do escopo

- Alterar o pipeline diário (`run_daily_pipeline.py`) ou o cron.
- Remover o modelo `Assinatura` do banco (permanece, não-restritivo).
- Notificação em tempo real (mantém-se o resumo diário atual).
- Usar MCP ou CLI do Resend (o SDK Python é a forma correta para envio no runtime).

## Tratamento de erro

- Falha ao enviar email → `ResendNotifier.enviar` loga a exceção e retorna `False`;
  o `notify_subscribers` registra o evento como não-enviado (sem criar
  `NotificacaoEnviada`), mantendo o comportamento atual de não duplicar.
- Sem `RESEND_API_KEY` → não envia, loga aviso (dev-safe).
- Erro de template → `notify_subscribers` captura e loga, sem abortar o pipeline
  diário (o `_notify_subscribers` já trata exceções do subprocess).

## Plano de migração/verificação

1. Implementar backend (models, notifiers, views, auth_views, template, migration).
2. Implementar frontend (remover demo/assinatura/telegram).
3. Rodar `manage.py makemigrations`/`migrate` e os testes existentes.
4. Validar localmente com `resend.dev` e `notify_subscribers --dry-run`.
5. Adicionar env vars na VPS + redeploy no EasyPanel.
6. Confirmar entrega real de email no dashboard do Resend.

Rollback: reverter os commits das mudanças; a migration RemoveField exige cuidado
(restaurar a coluna via migration reversa) — mas `Assinatura` e os dados de
preferência não são destruídos de forma irreversível neste escopo.