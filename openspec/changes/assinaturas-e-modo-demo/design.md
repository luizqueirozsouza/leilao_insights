## Context

Ver proposal.md - Why. O backend Django já expõe API de leitura (stats/filters/properties) e o pipeline diário (`run_daily_pipeline.py` → `ingest_dlt.py`) já grava eventos `ENTER`/`EXIT`/`UPDATE` na tabela `changes`. O frontend é uma SPA estática (sem build) hospedada em Cloudflare Pages, consumindo a API por CORS. Não há autenticação hoje. As specs (modo-demo, autenticacao, assinaturas, alertas-assinante, tipo-imovel, enriquecimento-imovel) definem o comportamento alvo.

## Goals / Non-Goals

**Goals:**
- Liberar acesso completo + alertas apenas para assinantes ativos, com modo demo para visitantes.
- Reutilizar a detecção de mudança já existente em `changes` para disparar alertas.
- Enriquecer a base sob demanda, com cache, sem sobrecarregar a Caixa.
- Normalizar tipo de imóvel em coluna estruturada e filtrável.

**Non-Goals:**
- Gateway de pagamento (ativação manual via admin nesta fase).
- Enriquecimento em lote de todo o acervo (é sob demanda).
- Suporte a recuperação de senha por email (pode vir depois).
- Migração do pipeline DLT/Telegram do operador.

## Decisions

### D1. Autenticação: sessão Django com cookie, SPA continua estática
O frontend continua sendo SPA estática, mas a autenticação usa a **sessão padrão do Django via cookie**, com CORS/SameSite configurado para aceitar o cookie cross-origin do domínio do frontend (Cloudflare Pages).
- Cookie de sessão com `SameSite=None; Secure` e CSRF habilitado (token CSRF via header `X-CSRFToken` obtido de um endpoint/set-cookie).
- Endpoints REST: `POST /api/registro`, `POST /api/login`, `POST /api/logout`, `GET /api/me`.
- **Alternativa considerada**: servir a SPA pelo próprio Django (templates) — eliminaria CORS/cookie cross-origin, mas mudaria o deploy (Cloudflare Pages) e o fluxo existente. **Alternativa considerada**: tokens JWT/DRF — adiciona dependência e gerenciamento de refresh; desnecessário para este escopo.
- **Motivo**: menor mudança no deploy atual; CORS custom já existe (`backend_django.core.middleware.CorsMiddleware`), basta permitir credenciais.

### D2. Modelo de dados
Novos modelos em `backend_django/auctions/models.py`:
- `Assinatura`: FK→`User` (um-para-um), `ativa` (bool), `data_inicio`, `data_fim` (validade opcional). Estado derivado: ativa se `ativa=True` e `data_fim` não venceu.
- `PreferenciaAlerta`: FK→`User`, com `uf`, `cidade`, `bairro`, `modalidade` (multi-seleção via JSON), `canal_email` (bool), `canal_whatsapp` (bool), `contato_whatsapp` (opcional). Uma assinatura pode ter várias preferências (linhas) OU uma linha com listas — escolhido: **uma linha por conjunto de filtros** (simples de cruzar com `changes`).
- `NotificacaoEnviada`: FK→`PreferenciaAlerta`, `tipo_evento` (ENTER/EXIT/UPDATE), `numero_imovel`, `uf`, `dt`, `canais` (JSON), `enviada_em`. Único por `(preferencia, numero_imovel, uf, tipo_evento, dt)` para dedupe.

Campos adicionados em `Auction`:
- `tipo_imovel` (`CharField`, choices: apartamento/casa/terreno/outro, `db_index=True`)
- `dados_enriquecidos` (`JSONField`, null/blank) + `dados_enriquecidos_at` (timestamp)

**Alternativa**: modelo de assinatura como campo booleano direto no User — rejeitado porque precisamos de validade e histórico para evoluir a monetização.

### D3. Normalização de tipo: na ingestão, com regra determinística
O tipo é derivado **durante a ingestão** (`pipeline/utils.py` / `build_index_columns`) a partir da descrição e endereço, com regra de precedência: se a descrição menciona explicitamente o tipo, usa; senão, heurística por palavras-chave (ex. "apartamento", "casa", "terreno", "lote", "gleba"); senão `outro`.
- Reaproveita a lógica de regex já existente em `views.py:_parse_desc`, movendo-a para o pipeline (persistida em vez de só renderizada).
- **Alternativa**: só sob demanda no detalhe — rejeitada porque tipo precisa estar disponível para filtro na listagem.
- Nota: tipos podem ser refinados depois pelo enriquecimento, mas o valor persistido é o determinístico da ingestão.

### D4. Dispatcher de alertas: passo pós-ingestão reutilizando `changes`
Novo passo (management command `notify_subscribers` e/ou chamada no `run_daily_pipeline.py` após o ingest) que:
1. Lê os eventos `ENTER`/`EXIT`/`UPDATE` do dia em `changes`.
2. Faz join com as preferências ativas dos assinantes (filtro UF/cidade/bairro/modalidade).
3. Para cada assinante+imóvel+evento correspondente, monta a mensagem e envia pelos canais configurados.
4. Registra em `NotificacaoEnviada` (dedupe por dt) — reexecução da mesma dt não reenvia.
- Canais abstraídos atrás de uma interface `Notifier` com implementações `EmailNotifier` (SMTP) e `WhatsAppNotifier` (API de provedor).
- **Alternativa**: disparar dentro do próprio `ingest_dlt.py` — evita, para manter o ingest focado em dados e o envio configurável/fail-isolated.

### D5. Canais de notificação: SMTP (email) + provedor WhatsApp via env vars
- Email: `django.core.mail` (SMTP) com `EMAIL_*` nas env vars. Em dev, console backend.
- WhatsApp: interface abstrata; primeira implementação via provedor (Twilio/WhatsApp Business) configurado por env vars. Se o provedor não estiver configurado, o canal WhatsApp é marcado como indisponível e o envio segue por email (log de aviso).

### D6. Enriquecimento sob demanda com cache
Endpoint `GET /api/property/<numero_imovel>` (ou similar) que:
1. Retorna imóvel + `dados_enriquecidos` se já em cache.
2. Se não cacheado, faz fetch em `detalhe-imovel.asp?Codigo=<numero>` (reusando sessão/headers de `pipeline/extrai.py`), parseia HTML (BeautifulSoup/lxml), extrai características e regras do certame, persiste em `dados_enriquecidos` e retorna.
- Rate-limit e timeout para não sobrecarregar a Caixa; falha → retorna dados básicos + flag de indisponível (spec).
- Conteúdo do detalhe (área, quartos, edital, regras) também alimenta refinamento de `tipo_imovel` se o determinístico for `outro`.

### D7. Modo demo no backend (fonte de verdade)
A limitação de amostra é aplicada **no backend**, não no frontend, para não vazar o acervo via API.
- Visitante: `_build_queryset`/`api_properties` retorna apenas um subconjunto de demonstração (ex. 30) determinístico por sessão (semente baseada em `session_key`), filtrando `Auction` por uma seleção de `(uf, cidade)` representativa.
- `api_properties` e `auction_list` consultam a amostra quando não autenticado; acesso completo só com assinatura ativa.
- Os endpoints de stats/filters refletem a amostra para visitantes (evita vazar contagem total).

## Risks / Trade-offs

- **Cookie cross-origin (D1)** → fragile se Cloudflare Pages não aceitar `SameSite=None; Secure`. Mitigação: configurar corretamente e, se necessário, migrar a SPA para ser servida pelo Django (plano B documentado).
- **Parsing da página da Caixa pode mudar** (D6) → parser centralizado e isolado em um módulo; falha de parse não quebra o app (retorna básico). Testar com amostra real.
- **WhatsApp depende de provedor pago** (D5) → primeiro entregar email funcional; WhatsApp implementado por interface para plugar provedor depois.
- **Normalização heurística de tipo imprecisa** (D3) → fallback `outro` + refinamento pelo enriquecimento; aceito nesta fase.
- **Sobrecarga da Caixa no enriquecimento** (D6) → somente sob demanda, com timeout/rate-limit e cache.
- **Notificações em volume** → dedupe por `dt` e envio assíncrono (fila simples/thread) para não travar o pipeline.

## Migration Plan

1. Criar migrações para novos modelos e novos campos de `Auction`.
2. Backfill `tipo_imovel` dos imóveis existentes (script único, reusa a mesma regra da ingestão).
3. Adicionar env vars: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `WHATSAPP_*` (opcional).
4. Deploy: backend primeiro; frontend depois de liberar os novos endpoints de auth/me.
5. Rollback: remover gate de assinatura/modo demo é uma reversão de config; novos campos são aditivos e não quebram o ingest existente.

## Open Questions

- Provedor específico de WhatsApp (Twilio vs. WhatsApp Business Cloud API) — decidir na implementação, sem mudar specs.
- Quantidade exata da amostra de demonstração (30 default; ajustável por env var).
- Recuperação de senha e confirmação de email — fora do escopo desta fase.
