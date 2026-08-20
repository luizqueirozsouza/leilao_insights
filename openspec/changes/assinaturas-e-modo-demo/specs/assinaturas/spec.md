## Purpose

Define o ciclo de vida da assinatura de um usuário (ativa ou inativa) para liberar acesso completo e recursos exclusivos, gerenciada manualmente pela administração.

## ADDED Requirements

### Requirement: Assinatura vinculada ao usuário
O sistema SHALL manter, para cada usuário, o estado da sua assinatura (ativa/inativa), com dados de validade.

#### Scenario: Usuário com assinatura ativa
- **WHEN** um usuário autenticado possui assinatura ativa
- **THEN** o sistema libera o acesso completo ao acervo e os recursos exclusivos de assinante

#### Scenario: Usuário sem assinatura ativa
- **WHEN** um usuário autenticado não possui assinatura ativa
- **THEN** o sistema o trata como não assinante, mantendo as restrições de modo demonstração

### Requirement: Ativação e desativação pelo administrador
O sistema SHALL permitir que a administração ative ou desative manualmente a assinatura de um usuário.

#### Scenario: Administrador ativa assinatura
- **WHEN** a administração marca a assinatura de um usuário como ativa
- **THEN** o usuário passa a ter acesso completo aos recursos de assinante imediatamente

#### Scenario: Administrador desativa assinatura
- **WHEN** a administração marca a assinatura de um usuário como inativa ou ela expira
- **THEN** o usuário perde o acesso completo e os recursos exclusivos

### Requirement: Assinatura expirada
O sistema SHALL tratar assinaturas cuja validade terminou como inativas.

#### Scenario: Assinatura vencida
- **WHEN** a data de validade da assinatura de um usuário é anterior à data atual
- **THEN** o sistema considera a assinatura inativa e restringe o acesso completo
