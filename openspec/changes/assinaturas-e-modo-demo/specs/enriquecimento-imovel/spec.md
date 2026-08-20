## Purpose

Enriquece a base de dados buscando, sob demanda, os dados detalhados de cada imóvel na página da Caixa, incluindo regras específicas do certame, e fazendo cache para consultas futuras.

## ADDED Requirements

### Requirement: Busca sob demanda dos detalhes
O sistema SHALL buscar os dados detalhados de um imóvel no site da Caixa quando o usuário solicitar o detalhe do imóvel, e armazenar o resultado em cache.

#### Scenario: Usuário abre o detalhe de um imóvel
- **WHEN** um usuário solicita o detalhe de um imóvel
- **THEN** o sistema busca os dados na página da Caixa, extrai os detalhes e os retorna

#### Scenario: Detalhe já em cache
- **WHEN** os detalhes do imóvel já foram buscados e armazenados anteriormente
- **THEN** o sistema retorna os dados do cache sem refazer a busca na Caixa

### Requirement: Extração de dados detalhados do imóvel
O sistema SHALL extrair da página da Caixa dados como área, quartos, vagas e demais características disponíveis.

#### Scenario: Dados detalhados extraídos
- **WHEN** a página de detalhe da Caixa contém características do imóvel (área, quartos, vagas, etc.)
- **THEN** o sistema extrai e disponibiliza essas características

### Requirement: Extração de regras do certame
O sistema SHALL extrair e armazenar as regras específicas do certame/edital a que o imóvel pertence.

#### Scenario: Regras do certame disponíveis
- **WHEN** a página de detalhe da Caixa contém informações do certame/edital e suas regras
- **THEN** o sistema extrai e disponibiliza essas regras

### Requirement: Falha de busca tratada
O sistema SHALL tratar a falha na busca dos detalhes sem quebrar a consulta, indicando indisponibilidade temporária dos dados detalhados.

#### Scenario: Página da Caixa indisponível
- **WHEN** a busca dos detalhes na Caixa falha
- **THEN** o sistema retorna os dados básicos do imóvel e indica que os detalhes estão temporariamente indisponíveis, permitindo nova tentativa posterior
