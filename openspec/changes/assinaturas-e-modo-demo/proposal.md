## Why

O app hoje expõe todo o acervo de imóveis leiloados da Caixa gratuitamente, sem retenção de valor: não há cadastro, nem modelo de receita, nem notificações proativas, e os dados de cada imóvel são rasos (a descrição crua, sem tipo estruturado nem detalhes do certame). Isso limita a monetização e a retenção de usuários.

## What Changes

- **Modo demonstração**: sem login, o frontend/API retorna apenas um subconjunto limitado e aleatório de imóveis (ex. 30), cobrindo vários estados/cidades, com banner de call-to-action para cadastro. O acesso completo fica restrito a usuários com assinatura ativa.
- **Autenticação**: registrar e logar por email + senha (Django padrão), com logout. Sessão usada para identificar o usuário.
- **Assinaturas**: modelo de assinatura ativa/inativa por usuário, gerenciada manualmente via Django Admin (sem gateway de pagamento nesta fase). Assinatura ativa libera acesso completo e os alertas.
- **Alertas de assinante**: assinante configura preferências de UF/cidade/bairro/modalidade e canal (email e/ou WhatsApp). A cada ingestão diária, os eventos `ENTER`/`EXIT`/`UPDATE` (tabela `changes`) são cruzados com as preferências e notificações são disparadas. Registro de envio para evitar duplicidade.
- **Normalização de tipo de imóvel**: classificar cada imóvel como `apartamento`, `casa`, `terreno` ou `outro`, persistido em coluna estruturada e usável em filtros.
- **Enriquecimento sob demanda**: ao clicar em um imóvel, buscar e parsear a página de detalhes da Caixa (`detalhe-imovel.asp?Codigo=...`), extraindo dados detalhados (área, quartos, edital/certame, regras específicas) e fazendo cache no banco.

## Capabilities

### New Capabilities

- `modo-demo`: Limitação de visibilidade do acervo para visitantes não autenticados.
- `autenticacao`: Registro, login e logout de usuários por email + senha.
- `assinaturas`: Ciclo de vida de assinatura (ativa/inativa) vinculada ao usuário e gerenciada pelo admin.
- `alertas-assinante`: Preferências de notificação e disparo de alertas (email/WhatsApp) em eventos de mudança.
- `tipo-imovel`: Classificação e filtro de imóveis por tipo (apartamento/casa/terreno/outro).
- `enriquecimento-imovel`: Extração sob demanda e cache de dados detalhados do site da Caixa.

### Modified Capabilities

Nenhuma — não há specs existentes no projeto (`openspec/specs/` vazio).

## Impact

- **Backend Django**: novos modelos (`Assinatura`, `PreferenciaAlerta`, `NotificacaoEnviada`), campos em `Auction` (`tipo_imovel`, `dados_enriquecidos`), endpoints de auth/me/assinatura/alertas, middleware de acesso, view de enriquecimento. Migrations novas.
- **Pipeline**: passo pós-ingestão para ler `changes` e disparar alertas de assinantes (management command ou integração no `run_daily_pipeline.py`).
- **Frontend**: telas de login/registro, estado de sessão, gerenciamento de alertas, banner de modo demo, modal de detalhe enriquecido. O frontend é SPA estático — exige definir a estratégia de auth (decisão em design.md).
- **Dependências**: SMTP para email; provedor de WhatsApp (Twilio/WhatsApp Business) — a definir; parsing HTML da Caixa (ex. BeautifulSoup/lxml).
- **Infra**: variáveis de ambiente novas (credenciais SMTP, WhatsApp). CI não é alterado.
