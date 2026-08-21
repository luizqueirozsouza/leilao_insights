## Purpose

Permite avaliar rapidamente a viabilidade financeira de um imóvel de leilão, combinando dados do anúncio com custos editáveis de aquisição, reforma e venda sem exigir autenticação ou assinatura.

## ADDED Requirements

### Requirement: Acesso público à calculadora
O sistema SHALL permitir que visitantes, usuários autenticados e assinantes abram a calculadora para qualquer imóvel que esteja disponível na interface.

#### Scenario: Visitante abre uma simulação
- **WHEN** um visitante seleciona a ação de simular aquisição em um imóvel visível
- **THEN** o sistema abre a calculadora sem exigir login, assinatura ou outro desbloqueio

### Requirement: Preenchimento com dados do imóvel
O sistema SHALL preencher a calculadora com os dados numéricos e características disponíveis no anúncio e nos detalhes enriquecidos do imóvel.

#### Scenario: Anúncio possui valor de avaliação e arrematação
- **WHEN** a calculadora é aberta para um imóvel com esses valores
- **THEN** os campos correspondentes aparecem preenchidos e permanecem editáveis

#### Scenario: Dado não está disponível
- **WHEN** um campo não possui valor no anúncio ou no enriquecimento
- **THEN** o campo aparece vazio ou com valor zero conforme sua natureza e o usuário pode informá-lo manualmente

### Requirement: Custos fixos ou percentuais
O sistema SHALL permitir que cada custo configurável seja informado como valor fixo ou como percentual sobre uma base explicitamente identificada.

#### Scenario: Usuário informa custo fixo
- **WHEN** o usuário escolhe o modo fixo e informa um valor
- **THEN** o sistema incorpora exatamente esse valor no cálculo

#### Scenario: Usuário informa custo percentual
- **WHEN** o usuário escolhe o modo percentual, informa uma taxa e seleciona a base de cálculo
- **THEN** o sistema calcula o custo aplicando a taxa à base selecionada e atualiza os resultados

### Requirement: Cálculo do resultado financeiro
O sistema SHALL exibir o investimento total, o custo total de venda, o lucro estimado, a margem e o ROI com base nos dados atuais do formulário.

#### Scenario: Simulação com lucro
- **WHEN** o valor estimado de venda é maior que o investimento total somado aos custos de venda
- **THEN** o sistema exibe lucro positivo, margem positiva e ROI correspondente

#### Scenario: Simulação com prejuízo
- **WHEN** o valor estimado de venda é menor que o investimento total somado aos custos de venda
- **THEN** o sistema exibe resultado negativo sem bloquear a simulação

### Requirement: Atualização imediata e temporária
O sistema SHALL recalcular os resultados quando qualquer valor, modo, taxa ou base for alterado e SHALL manter a simulação apenas durante a sessão atual do popup.

#### Scenario: Usuário edita um custo
- **WHEN** o usuário altera um valor ou percentual
- **THEN** os totais e indicadores são atualizados sem recarregar a página

#### Scenario: Usuário fecha a calculadora
- **WHEN** o usuário fecha o popup
- **THEN** a simulação é descartada e não é persistida no servidor
