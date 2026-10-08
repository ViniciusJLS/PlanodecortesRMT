# Referência AUX TRAMO e Excel final do subparque

O aplicativo reconhece o formato da aba **PLANO DE CORTE** com **POSTE na coluna I** e **DISTÂNCIA TRAMO na coluna L**. Essa sequência é transformada em trechos explícitos De/Para e, em seguida, em registros das fases A, B e C.

## Leitura do formato enviado

- **De:** poste válido anterior; no primeiro vão positivo de cada tramo, SE (ou origem informada).
- **Para:** poste de I na linha atual.
- **Distância linear:** L da linha atual (linha Para).
- **L = 0:** a estrutura dessa linha não existe no traçado e não entra em De nem Para. Reinicia o tramo; a primeira distância positiva seguinte é usada no vão SE → primeiro poste válido.
- Marcadores incompletos como `P.` e linhas sem poste não geram trechos. Valores negativos, poste incompleto com distância positiva e fórmulas sem resultados salvos bloqueiam a prévia.

Por exemplo, no arquivo AUX enviado, I4 = P.0/8D (AD5), I5 = P.0/7D (AD4) e L5 = 50,09 m. Como L4 é zero, P.0/8D (AD5) é excluído. O trecho importado é **SE → P.0/7D (AD4), 50,09 m**. A ordem de lançamento segue a ordem das linhas do bloco I/L, que no arquivo enviado é descendente na sequência de postes. O aplicativo não usa o bloco espelhado C/F.

Na referência enviada, o cabeçalho é a linha 3, os postes estão nas linhas 4–74 e a conversão produz 66 vãos físicos / 198 registros de fase. Caminhos desconectados permanecem separados na otimização e consolidação. Blocos com ligação física inequívoca em DE/PARA são unidos para não exigir uma troca de bobina artificial na fronteira. Cortes obrigatórios continuam obrigatórios; estruturas de 1000/gaveta e marcações azuis não permitem iniciar ou terminar uma bobina. Os dados de origem são preservados ao salvar alterações na página Traçado.

## Como usar

1. Selecione a obra e o subparque.
2. Configure circuito, nível, tipo de instalação, rota, condutor, folga, reserva e restrições de corte.
3. Envie a referência Excel e selecione a aba **PLANO DE CORTE**. O formato **AUX TRAMO: postes em I e distância em L** será selecionado automaticamente quando o cabeçalho corresponder.
4. Confira o intervalo de linhas e a origem dos tramos (SE por padrão). As linhas zero são ignoradas, e o primeiro L positivo fornece a distância até o primeiro poste válido.
5. Confira os pares De/Para e as distâncias na prévia e importe o lançamento.
6. Revise as restrições da obra e clique em **Calcular bobinas e pontos de corte**. As bobinas são atribuídas pelo solucionador usando o estoque cadastrado da obra.
7. Após um plano válido, use **Baixar Excel final deste subparque**.

## Conteúdo do Excel final

- **PLANO DE CORTE:** todos os trechos do subparque, organizados por circuito, nível, rota e ordem, com fases A/B/C, bobina alocada, De, Para, distância linear, folga, reserva, lançamento e origem na referência.
- **LANÇAMENTOS:** cortes contínuos com bobina, início/fim, soma linear, acréscimos e distância de projeto arredondada uma vez por lançamento.
- **RESUMO_BOBINAS:** bobinas usadas no subparque, consumo neste subparque, reservas de toda a obra e saldo da obra. O saldo considera também os outros subparques para evitar aparentar disponibilidade já reservada.
- **CRITÉRIOS:** regras de cálculo, status do solucionador e identificação dos dados.

O arquivo final é um novo relatório tabular calculado pelo aplicativo. A referência original continua disponível para download. O download final só é oferecido se o subparque possuir cortes em um plano atual e validado. Após editar entradas, é necessário recalcular.

## Validação

Os testes verificam leitura I/L, uso da distância da linha Para, interrupções de tramo, preservação das três fases, valores inválidos, correspondência entre bobinas exportadas e plano calculado, exportação limitada ao subparque selecionado e o fluxo da interface desde a prévia até o download.

Referências AUX já salvas pela versão anterior são corrigidas usando o Excel original armazenado: as origens que correspondem exatamente a linhas L=0 passam a ser SE. A correção preserva IDs, metragens, condutores, bobinas e demais registros; não sobrescreve origens editadas manualmente. O plano anterior precisa ser recalculado.
