# Critérios operacionais de lançamento

Na obra selecionada, abra **Critérios de corte**, configure as sobras, cadastre a proximidade física dos pares de subparques e informe a ordem real de execução (um nome por linha). Salve os critérios e gere novamente o plano. Para repartir o estoque entre parques, prefira **Todos os subparques**. A otimização de um único parque preserva as alocações dos demais e considera suas bobinas compartilhadas.

## Prioridades

1. Minimizar lançamentos contínuos, contados por fase, reduzindo preparações e trocas.
2. Maximizar bobinas cujo saldo disponível é consumido em um único lançamento, terminando dentro da sobra tolerada.
3. Minimizar o total de ocorrências de sobra intermediária e de lançamento curto. Cada ocorrência conta uma unidade.
4. Minimizar o índice de transporte entre parques que compartilham bobinas.
5. Desempatar pela metragem de estoque mobilizada.

São resoluções sucessivas: uma etapa posterior não pode piorar o resultado obtido nas anteriores. Capacidade, condutor, continuidade, cortes obrigatórios e estruturas sem corte são restrições obrigatórias. As preferências operacionais permitem exceções para concluir um plano viável. Não há estimativa monetária ou de horas da equipe.

## Limites iniciais, ajustáveis por obra

| Condição | Avaliação |
|---|---|
| Saldo zero | Bobina esgotada |
| Saldo positivo até 60 m | Sobra tolerada |
| Saldo maior que 60 m e até 500 m | Sobra intermediária a evitar |
| Saldo acima de 500 m | Sobra reutilizável |
| Lançamento até 500 m | Operação curta a evitar |

Exemplo verificado: duas bobinas de 1455 m atendendo vãos de 900, 425 e 475 m. Em condições equivalentes, o cálculo escolhe lançamentos de 900 + 900 m, deixando 555 m em cada bobina, em vez de 1325 + 475 m com saldos de 130 e 980 m. Se o poste aos 900 m não permite corte, o cálculo respeita essa restrição e aponta a sobra intermediária.

## Proximidade e ordem

A proximidade é cadastrada pelo usuário: Próximos (1), Intermediários (2), Não informada (3) ou Distantes (4). Os números são índices relativos, não quilômetros ou preços. Um par não informado nunca é presumido próximo pela numeração dos parques.

Com a ordem completa dos parques do plano, contam somente os deslocamentos entre parques consecutivos atendidos por cada bobina. Sem ordem completa, contam os pares de parques que compartilham a bobina, sem supor uma rota física. As relações são simétricas.

## Resultado e rastreabilidade

O painel **Análise operacional da obra** mostra sobras intermediárias, lançamentos curtos, bobinas em lançamento único e compartilhamentos. Os arquivos Excel incluem os limites e critérios usados. O resumo do Excel de um subparque considera o plano global da obra, assim como o estoque compartilhado.

O cálculo só declara ótimo quando todas as prioridades foram comprovadas dentro do tempo disponível. Se o tempo acabar, conserva a solução integral já encontrada e informa que a otimização não foi comprovada. O modo rápido retorna uma solução viável sem garantir essas prioridades. Os antigos pesos deixam de controlar o cálculo; planos anteriores devem ser gerados novamente para aplicar esta versão.

Metragem real continua substituindo a tolerância contratual de 3%. O consumo é calculado a partir das distâncias lineares, com folgas e reservas existentes e arredondamento apenas por lançamento contínuo.
