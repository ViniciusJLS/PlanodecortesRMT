# Referência AUX TRAMO e Excel final do subparque

O aplicativo reconhece o formato da aba **PLANO DE CORTE** com **POSTE na coluna I** e **DISTÂNCIA TRAMO na coluna L**. Essa sequência é transformada em trechos explícitos De/Para e, em seguida, em registros das fases A, B e C.

## Leitura do formato enviado

- **De:** poste de I na linha anterior.
- **Para:** poste de I na linha atual.
- **Distância linear:** L da linha atual (linha Para).
- **L = 0:** início de um novo tramo; não cria trecho de comprimento zero e não liga o novo ramal ao anterior.
- Linhas sem poste e marcadores incompletos como `P.` interrompem a sequência e não viram trechos. Distância positiva sem poste anterior, poste incompleto com distância positiva, valores negativos ou fórmulas sem resultados salvos bloqueiam a prévia.

Por exemplo, no arquivo AUX enviado, I4 = P.0/8D (AD5), I5 = P.0/7D (AD4) e L5 = 50,09 m. O trecho importado é **P.0/8D (AD5) → P.0/7D (AD4), 50,09 m**. A ordem de lançamento segue a ordem das linhas do bloco I/L, que no arquivo enviado é descendente na sequência de postes. O aplicativo não usa o bloco espelhado C/F.

Na referência enviada, o cabeçalho é a linha 3, os postes estão nas linhas 4–74 e a conversão produz 66 vãos físicos / 198 registros de fase. Os diferentes tramos permanecem separados também na otimização e consolidação, mesmo se algum poste coincidir nas fronteiras. Os dados de origem são preservados ao salvar alterações na página Traçado.

## Como usar

1. Selecione a obra e o subparque.
2. Configure circuito, nível, tipo de instalação, rota, condutor, folga, reserva e restrições de corte.
3. Envie a referência Excel e selecione a aba **PLANO DE CORTE**. O formato **AUX TRAMO: postes em I e distância em L** será selecionado automaticamente quando o cabeçalho corresponder.
4. Confira o intervalo de postes. Inclua a linha inicial de cada tramo para que o primeiro vão positivo tenha as duas extremidades conhecidas.
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
