## Why

O painel já oferece detalhes enriquecidos sob demanda e alertas para assinantes, mas esses recursos estão pouco visíveis no fluxo principal. Além disso, o usuário precisa sair do anúncio ou fazer contas externas para avaliar rapidamente se uma aquisição pode ser vantajosa.

Esta mudança aproxima descoberta e decisão: alertas ficam acessíveis no cabeçalho e qualquer visitante pode simular os custos e o resultado estimado de um imóvel da amostra ou do acervo.

## What Changes

- Mover o acesso a "Meus alertas" para a área superior, ao lado do usuário autenticado.
- Manter a extração de detalhes do certame sob demanda, acionada quando o detalhe for aberto e reutilizando dados já armazenados em cache.
- Adicionar uma ação "Simular aquisição" ao fluxo de detalhes de cada imóvel.
- Abrir a simulação em um popup sem exigir autenticação ou assinatura.
- Preencher a simulação com dados disponíveis no anúncio e no enriquecimento, mantendo todos os valores editáveis.
- Permitir que custos sejam informados como valor fixo ou percentual, com indicação da base de cálculo.
- Calcular investimento total, custos de venda, valor estimado de venda, lucro estimado, margem e ROI.
- Manter as simulações apenas em memória enquanto o popup estiver aberto; não haverá persistência nesta etapa.

## Capabilities

### New Capabilities

- `calculadora-aquisicao`: simulação pública e editável dos custos, valor estimado de venda e retorno de uma aquisição em leilão.

### Modified Capabilities

Nenhuma capacidade existente terá requisitos de negócio alterados. O posicionamento visual dos alertas e a integração do detalhe com a calculadora serão ajustes de interface.

## Impact

- Frontend estático: cabeçalho, cards/detalhes, popup da calculadora, estado temporário e fórmulas de simulação.
- Backend Django: possivelmente apenas exposição ou normalização de campos existentes, caso algum dado do anúncio não esteja disponível no endpoint de detalhe.
- API de detalhe do imóvel: reutilização de `GET /api/property/<numero>` e do cache de enriquecimento existente.
- CSS responsivo: novo popup, formulário de custos e apresentação dos resultados em desktop e mobile.
- Não serão adicionadas dependências externas, gateway de pagamento ou persistência de simulações.
