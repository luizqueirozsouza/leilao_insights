## Purpose

Permite que assinantes configurem preferências de imóveis (estados, cidades, bairros e modalidades) e recebam notificações por email e/ou WhatsApp sempre que houver mudança, adição ou remoção de imóveis compatíveis.

## ADDED Requirements

### Requirement: Preferências de notificação
O sistema SHALL permitir que um assinante configure filtros de interesse (UF, cidade, bairro, modalidade) e os canais de recebimento (email e/ou WhatsApp).

#### Scenario: Assinante define preferências
- **WHEN** um assinante autenticado informa UF, cidade, bairro e modalidade de interesse e escolhe os canais
- **THEN** o sistema persiste essas preferências para uso nos disparos de alerta

#### Scenario: Assinante altera preferências
- **WHEN** um assinante modifica as preferências salvas
- **THEN** o sistema passa a usar as novas preferências nos próximos disparos

### Requirement: Disparo em eventos de mudança
O sistema SHALL disparar notificações quando houver adição (ENTER), remoção (EXIT) ou alteração (UPDATE) de imóveis que correspondam às preferências do assinante, após cada ingestão diária.

#### Scenario: Imóvel novo compatível adicionado
- **WHEN** a ingestão diária registra um novo imóvel que corresponde às preferências de um assinante
- **THEN** o sistema envia uma notificação ao assinante informando a adição

#### Scenario: Imóvel compatível removido
- **WHEN** a ingestão diária registra a remoção de um imóvel que correspondia às preferências de um assinante
- **THEN** o sistema envia uma notificação ao assinante informando a remoção

#### Scenario: Imóvel compatível alterado
- **WHEN** a ingestão diária registra alteração (ex. preço) em um imóvel compatível com as preferências
- **THEN** o sistema envia uma notificação ao assinante informando a mudança

### Requirement: Notificação por email e WhatsApp
O sistema SHALL entregar as notificações pelos canais configurados pelo assinante (email e/ou WhatsApp), conforme a disponibilidade de cada canal.

#### Scenario: Assinante com canal email
- **WHEN** um assinante configurou apenas o canal email
- **THEN** o sistema envia a notificação somente por email

#### Scenario: Assinante com canais email e WhatsApp
- **WHEN** um assinante configurou os canais email e WhatsApp
- **THEN** o sistema envia a notificação por ambos os canais

### Requirement: Evitar notificações duplicadas
O sistema SHALL registrar cada notificação enviada para não enviar a mesma notificação mais de uma vez.

#### Scenario: Reexecução da ingestão do mesmo dia
- **WHEN** a ingestão de uma data é executada novamente
- **THEN** o sistema não reenvia notificações já enviadas para os mesmos eventos e assinantes

### Requirement: Acesso a alertas exige assinatura ativa
O sistema SHALL restringir a configuração e o recebimento de alertas a usuários com assinatura ativa.

#### Scenario: Não assinante tenta configurar alerta
- **WHEN** um usuário autenticado sem assinatura ativa tenta configurar alertas
- **THEN** o sistema bloqueia a configuração e informa que alertas exigem assinatura
