## 1. Modelos de dados e migrações

- [x] 1.1 Adicionar campos `tipo_imovel`, `dados_enriquecidos`, `dados_enriquecidos_at` ao modelo `Auction` e criar migração; verificar com `makemigrations`/`migrate` e com `Auction` acessível no admin
- [x] 1.2 Criar modelo `Assinatura` (FK→User one-to-one, ativa, data_inicio, data_fim) e migração; verificar criação/listagem no admin
- [x] 1.3 Criar modelo `PreferenciaAlerta` (FK→User, uf/cidade/bairro/modalidade, canal_email, canal_whatsapp, contato_whatsapp) e migração; verificar no admin
- [x] 1.4 Criar modelo `NotificacaoEnviada` (FK→PreferenciaAlerta, tipo_evento, numero_imovel, uf, dt, canais, enviada_em, unique de dedupe) e migração; verificar no admin
- [x] 1.5 Criar script/management command de backfill de `tipo_imovel` para imóveis existentes; verificar que todos os registros têm tipo preenchido

## 2. Autenticação e sessão

- [x] 2.1 Configurar CORS com credenciais e cookie de sessão cross-origin (SameSite=None; Secure) e CSRF header; verificar requisição autenticada cross-origin funcionando
- [x] 2.2 Implementar endpoints `POST /api/registro` (unicidade de email), `POST /api/login`, `POST /api/logout`, `GET /api/me`; verificar fluxo completo via API/curl
- [x] 2.3 Adicionar templates/páginas de login e registro no frontend e estado de sessão na SPA; verificar cadastro/login/logout na UI

## 3. Modo demonstração

- [x] 3.1 Implementar amostra de demonstração determinística por sessão (ex. 30 imóveis, cobrindo UF/cidade) e aplicar em `api_properties` e `auction_list` para não autenticados; verificar que visitante só vê a amostra
- [x] 3.2 Ajustar endpoints de stats/filters para refletir a amostra para visitantes (não vazar contagem total); verificar stats da amostra
- [x] 3.3 Adicionar banner/aviso de modo demonstração com CTA de cadastro no frontend; verificar exibição para visitante

## 4. Acesso completo por assinatura

- [x] 4.1 Implementar verificação de assinatura ativa (ativa=True e data_fim não vencida) e gate de acesso completo nos endpoints de listagem/detalhe; verificar assinante vê tudo e não assinante só amostra
- [x] 4.2 Registrar `Assinatura` no admin com ativação/desativação manual e expiração automática; verificar que assinatura vencida perde acesso

## 5. Normalização de tipo de imóvel

- [x] 5.1 Implementar regra determinística de tipo (apartamento/casa/terreno/outro) no pipeline de ingestão (`build_index_columns`), reusando lógica de regex existente; verificar tipo correto para casos de cada categoria
- [x] 5.2 Adicionar campo `tipo_imovel` ao UPSERT do `ingest_dlt.py`; verificar que novos ingressos populam o tipo
- [x] 5.3 Adicionar filtro por tipo nos endpoints de listagem/filters e no frontend; verificar filtro por tipo retorna imóveis corretos
- [x] 5.4 Exibir tipo normalizado no card do imóvel (frontend); verificar exibição

## 6. Alertas de assinante

- [x] 6.1 Implementar interface `Notifier` com `EmailNotifier` (SMTP) e `WhatsAppNotifier` (provedor por env vars, opcional); verificar envio por email em dev (console backend)
- [x] 6.2 Implementar management command `notify_subscribers` que cruza `changes` do dia com preferências ativas e dispara notificações com dedupe via `NotificacaoEnviada`; verificar que reexecução da mesma dt não reenvia
- [x] 6.3 Integrar `notify_subscribers` no `run_daily_pipeline.py` após o ingest; verificar disparo ao simular ENTER/EXIT/UPDATE
- [x] 6.4 Implementar endpoints CRUD de preferências de alerta (restrito a assinantes) e UI de gerenciamento no frontend; verificar que não assinante é bloqueado

## 7. Enriquecimento sob demanda

- [x] 7.1 Implementar módulo de parser da página de detalhe da Caixa (fetch com sessão de `extrai.py` + BeautifulSoup) extraindo características e regras do certame; verificar parse contra página real
- [x] 7.2 Implementar endpoint de detalhe (`GET /api/property/<numero>`) com cache em `dados_enriquecidos` e tratamento de falha (retorna básico + indisponível); verificar primeira busca popula cache e segunda usa cache
- [x] 7.3 Adicionar modal/aba de detalhe enriquecido no frontend ao clicar no imóvel; verificar exibição dos dados extraídos
- [x] 7.4 Refinar `tipo_imovel` para `outro` quando o enriquecimento identificar tipo; verificar atualização

## 8. Verificação final

- [x] 8.1 Rodar `makemigrations --check` e `migrate` sem erros e verificar app inicia
- [x] 8.2 Executar teste manual do fluxo completo: visitante vê amostra → cadastro → assinante ativa no admin → acesso completo → configura alerta → ingestão com evento → notificação recebida → detalhe enriquecido
