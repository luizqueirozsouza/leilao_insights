## Purpose

Classifica cada imóvel em um tipo normalizado (apartamento, casa, terreno ou outro) e permite filtrar e exibir o acervo por tipo.

## ADDED Requirements

### Requirement: Classificação de tipo de imóvel
O sistema SHALL atribuir a cada imóvel um tipo normalizado entre: apartamento, casa, terreno e outro.

#### Scenario: Imóvel identificado como apartamento
- **WHEN** a descrição ou os dados do imóvel indicam que se trata de um apartamento
- **THEN** o sistema classifica o imóvel como `apartamento`

#### Scenario: Imóvel identificado como casa
- **WHEN** a descrição ou os dados do imóvel indicam que se trata de uma casa
- **THEN** o sistema classifica o imóvel como `casa`

#### Scenario: Imóvel identificado como terreno
- **WHEN** a descrição ou os dados do imóvel indicam que se trata de um terreno/lote
- **THEN** o sistema classifica o imóvel como `terreno`

#### Scenario: Tipo não identificável
- **WHEN** não é possível identificar o tipo do imóvel
- **THEN** o sistema classifica o imóvel como `outro`

### Requirement: Filtro por tipo de imóvel
O sistema SHALL permitir filtrar o acervo de imóveis por tipo normalizado.

#### Scenario: Filtro por tipo
- **WHEN** um usuário seleciona um ou mais tipos de imóvel
- **THEN** o sistema retorna apenas imóveis que correspondem aos tipos selecionados

### Requirement: Exibição do tipo
O sistema SHALL exibir o tipo normalizado do imóvel na listagem e no detalhe.

#### Scenario: Tipo exibido no card do imóvel
- **WHEN** um imóvel é listado
- **THEN** o sistema exibe o tipo normalizado do imóvel
