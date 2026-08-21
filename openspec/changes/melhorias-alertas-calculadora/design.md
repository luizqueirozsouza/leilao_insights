## Context

O frontend é uma SPA estática sem build, com estado mantido em `frontend/app.js`, popups implementados no HTML e estilos centralizados em `frontend/styles.css`. O endpoint `GET /api/property/<numero>` já busca e armazena dados enriquecidos sob demanda. Os cards recebem dados básicos de `GET /api/properties`.

## Goals / Non-Goals

**Goals:**

- Reutilizar o endpoint de detalhe e os dados já carregados, evitando uma nova fonte de dados para a calculadora.
- Implementar uma simulação client-side, pública, editável e responsiva.
- Manter os alertas visíveis no cabeçalho sem alterar as regras atuais de assinatura.
- Diferenciar claramente dados originados do anúncio de valores editados pelo usuário.

**Non-Goals:**

- Persistir simulações, criar histórico ou sincronizá-las entre dispositivos.
- Definir valores oficiais de ITBI, cartório ou impostos por município.
- Fazer avaliação automática de mercado ou integrar uma fonte externa de preços.
- Alterar o pipeline de ingestão ou a rotina de notificações.

## Decisions

### Estado temporário no frontend

A calculadora será alimentada por um objeto de estado criado ao abrir o popup. Cada campo terá valor, modo (`fixed` ou `percent`) e, quando percentual, uma base de cálculo. O estado será descartado no fechamento.

Alternativa considerada: salvar uma entidade de simulação no backend. Foi rejeitada porque a necessidade inicial é exploração rápida e a persistência adicionaria modelo, autenticação, endpoints e regras de atualização sem benefício necessário.

### Dados do anúncio como valores iniciais

O botão será disponibilizado no detalhe do imóvel, depois que os dados básicos estiverem disponíveis; dados enriquecidos já obtidos serão usados quando existirem. O valor de arrematação e o valor de avaliação serão preservados como campos distintos. O valor estimado de venda será um campo editável independente, sem ser inferido automaticamente a partir da avaliação.

Alternativa considerada: abrir a calculadora somente após nova busca de enriquecimento. Foi rejeitada para não tornar a calculadora dependente da disponibilidade da Caixa; campos ausentes podem ser preenchidos manualmente.

### Modelo de custos

Custos de aquisição e custos de venda serão grupos separados. Cada linha terá descrição, modo, valor/taxa e base quando aplicável. Bases sugeridas para a primeira versão:

- aquisição: valor de arrematação ou valor de avaliação;
- reforma: valor de arrematação, valor de avaliação ou área, quando uma estimativa por m² for usada;
- venda: valor estimado de venda;
- outros: valor de arrematação, valor estimado de venda ou investimento total.

O usuário poderá escolher a base para evitar que o sistema assuma regras tributárias municipais. Valores percentuais serão convertidos para valores monetários antes da soma dos resultados.

### Fórmulas

```text
investimento_total = arrematacao + custos_aquisicao + reforma + outros_custos
custos_venda = corretagem + impostos_venda + outros_custos_venda
resultado = valor_estimado_venda - investimento_total - custos_venda
margem = resultado / valor_estimado_venda * 100
roi = resultado / investimento_total * 100
```

Quando a base de um indicador for zero ou estiver ausente, o sistema exibirá `-` em vez de dividir por zero. Campos monetários não aceitarão valores negativos.

### Posicionamento de alertas

O controle "Meus alertas" será movido da grade de filtros para o agrupamento de conta do cabeçalho. A regra de visibilidade continuará dependente de autenticação e assinatura ativa; a mudança é apenas de descoberta e acesso.

## Risks / Trade-offs

- **Estimativas podem ser interpretadas como valores oficiais** -> rotular resultados como estimados e deixar custos editáveis; não prometer precisão fiscal ou jurídica.
- **Bases percentuais podem gerar interpretações erradas** -> exibir a base ao lado de cada taxa e atualizar o valor monetário calculado na mesma linha.
- **Dados enriquecidos podem estar indisponíveis** -> permitir abertura com dados básicos e preenchimento manual.
- **Popup extenso em telas pequenas** -> usar seções recolhíveis ou fluxo vertical responsivo e manter o resumo financeiro visível.

## Migration Plan

1. Alterar o markup e o estilo do cabeçalho para acomodar o botão de alertas.
2. Adicionar a ação, o popup e o estado temporário da calculadora no frontend.
3. Reutilizar os dados retornados pelo detalhe e validar o cálculo com campos preenchidos e vazios.
4. Publicar o frontend sem migração de banco ou alteração obrigatória de configuração.

Rollback: remover a ação e o popup da calculadora e restaurar o botão de alertas na área anterior; nenhuma informação persistida precisará ser revertida.
