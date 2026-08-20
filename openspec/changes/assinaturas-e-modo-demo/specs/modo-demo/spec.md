## Purpose

Limita a quantidade e o alcance de imóveis visíveis para visitantes não autenticados, exibindo apenas uma amostra de demonstração e incentivando o cadastro.

## ADDED Requirements

### Requirement: Amostra de demonstração para visitantes
Para usuários não autenticados, o sistema SHALL retornar apenas um subconjunto limitado de imóveis (por padrão 30), selecionado de forma a cobrir uma variedade de estados e cidades.

#### Scenario: Visitante consulta a lista de imóveis
- **WHEN** um usuário não autenticado solicita a lista de imóveis
- **THEN** o sistema retorna no máximo 30 imóveis de demonstração, distribuídos entre diferentes estados e cidades

#### Scenario: Amostra permanece estável por sessão
- **WHEN** um visitante navega pela lista de demonstração dentro da mesma sessão
- **THEN** o mesmo conjunto de imóveis de amostra é apresentado, para consistência de navegação e paginação

### Requirement: Acesso completo exige autenticação
O sistema SHALL ocultar a totalidade do acervo para visitantes não autenticados, liberando acesso completo apenas para usuários autenticados com assinatura ativa.

#### Scenario: Visitante tenta acessar imóvel fora da amostra
- **WHEN** um usuário não autenticado solicita acesso a um imóvel fora do conjunto de demonstração
- **THEN** o sistema não retorna os dados completos do imóvel e indica a necessidade de login/assinatura

### Requirement: Indicação de modo demonstração
O sistema SHALL comunicar ao visitante que ele está vendo apenas uma amostra e que o acesso completo depende de cadastro e assinatura.

#### Scenario: Visitante visualiza a amostra
- **WHEN** um usuário não autenticado visualiza a lista de demonstração
- **THEN** o sistema exibe uma indicação clara (banner/aviso) de que está em modo demonstração com acesso parcial
