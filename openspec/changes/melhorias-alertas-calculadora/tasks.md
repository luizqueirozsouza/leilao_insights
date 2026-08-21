## 1. Estrutura da Interface

- [x] 1.1 Mover o botão "Meus alertas" da grade de filtros para o agrupamento da conta no cabeçalho e verificar que sua visibilidade para assinantes permanece correta.
- [x] 1.2 Adicionar o popup da calculadora com campos de anúncio, aquisição, reforma, venda e resumo financeiro; verificar abertura e fechamento por botão, overlay e tecla de fechamento conforme o padrão dos modais existentes.
- [x] 1.3 Adicionar estilos responsivos para o popup, linhas de custo fixo/percentual e resumo; verificar visualização utilizável em viewport desktop e mobile.

## 2. Estado E Cálculos

- [x] 2.1 Criar o estado temporário da simulação e inicializá-lo com dados básicos e enriquecidos do imóvel, mantendo valor de avaliação, arrematação e venda estimada separados; verificar que campos ausentes podem ser preenchidos manualmente.
- [x] 2.2 Implementar linhas de custos com modo fixo ou percentual, seleção de base e conversão para valor monetário; verificar cálculo correto para cada modo e rejeição de valores monetários negativos.
- [x] 2.3 Implementar investimento total, custos de venda, resultado, margem e ROI com proteção contra divisão por zero; verificar cenários de lucro, prejuízo e dados incompletos.
- [x] 2.4 Conectar eventos de edição, troca de modo e troca de base ao recálculo imediato sem recarregar a página; verificar que fechar o popup descarta a simulação.

## 3. Integração Do Fluxo

- [x] 3.1 Adicionar a ação "Simular aquisição" ao detalhe do imóvel e garantir que ela funciona com dados enriquecidos em cache, dados recém-extraídos e falha de enriquecimento; verificar os três fluxos no popup.
- [x] 3.2 Garantir que a ação e a calculadora funcionam para visitantes em modo demonstração sem chamada de autenticação ou assinatura; verificar o fluxo com uma propriedade visível para visitante.
- [x] 3.3 Revisar a integração do botão de alertas após a mudança de posição e verificar que o modal de alertas, criação e remoção de preferências continuam funcionando.

## 4. Verificação Final

- [x] 4.1 Executar validação OpenSpec e revisar os artefatos da mudança para garantir que todos os requisitos possuem cenários correspondentes.
- [x] 4.2 Fazer uma verificação manual completa no frontend em desktop e mobile, cobrindo detalhe, calculadora, cálculos, alertas e fechamento dos popups.
