# Excel de referência e otimização por subparque

## Fluxo de trabalho

1. Abra **Subparques**. Se necessário, use **Cadastrar subparque** para criar um parque vazio, sem importar o controle completo.
2. Selecione o parque e abra **Configurar lançamento e importar Excel deste subparque**.
3. Escolha circuito C01–C34, nível 1–3, instalação aérea/subterrânea, rota e condutor. Configure folga, reserva e corte padrão. Esses controles definem os dados do lançamento; os filtros abaixo apenas selecionam a consulta.
4. Envie o Excel `.xlsx` ou `.xlsm` daquele subparque. Também é possível baixar um modelo pelo aplicativo. O modelo tem cabeçalho na linha 4 e dados a partir da linha 5; substitua os dois trechos de exemplo.
5. Escolha a aba e a linha do cabeçalho. Associe **De**, **Para** e **Distância linear**. Associe as demais colunas disponíveis ou use os padrões da configuração. Não associe Distância de projeto como distância linear.
6. Ajuste a primeira e a última linha para excluir notas, totais e outros blocos. A visualização das linhas originais ajuda a conferir o intervalo. Colunas associadas de circuito, nível e tipo filtram os registros para a configuração selecionada; sem associação, os registros recebem a configuração escolhida.
7. Escolha uma linha por trecho (o aplicativo gera A/B/C) ou uma linha por fase (o Excel já contém A/B/C). Confira a prévia antes de clicar em **Importar referência para este lançamento**.
8. Repita para os demais circuitos, níveis, tipos e rotas do parque. O escopo substituído é exatamente **subparque + circuito + nível + tipo + rota**; reimportar o mesmo escopo pede confirmação e não acumula cópias. Outros escopos são preservados.
9. Confira as tabelas aérea e subterrânea e revise amarrações, travessias, folgas e reservas. Use os formulários de edição e a página **Critérios de corte** para corrigir restrições.
10. Em **Otimizar plano de corte**, escolha apenas este subparque ou todos os subparques, confirme a revisão dos critérios e clique em **Calcular bobinas e pontos de corte**.
11. Confira as bobinas nas tabelas e os lançamentos consolidados abaixo. Baixe o controle ou o entregável Excel na própria página. As exportações contêm o plano validado de todos os parques cadastrados, com o estoque compartilhado considerado.

## Referência, estoque e critérios

O Excel de referência fornece o traçado, não precisa trazer bobinas já atribuídas e não substitui o estoque. Cadastre as bobinas na página **Bobinas** ou importe previamente o controle completo. O condutor e o tipo do estoque devem corresponder aos trechos para que haja bobinas compatíveis.

Se a referência já contém fases, não escolha o modo que gera A/B/C novamente. O aplicativo verifica as três fases de cada trecho, valores positivos e ordens sem duplicidade. Células de fórmulas precisam ter resultados calculados e salvos pelo Excel; o aplicativo não executa fórmulas nem macros.

Na folga, o formato padrão é fração: `0,05` representa 5%. Marque a opção específica somente se a coluna usa `5` para representar 5%. Informe **reserva total** ou associe as **sobras detalhadas**, sem duplicar as duas formas. Sobras são totais em metros; quantidades não são multiplicadas novamente.

Ao trazer um parque que antes estava apenas no histórico do resumo, o consumo histórico desse parque é retirado do consumo anterior e os trechos cadastrados passam a determinar seu consumo planejado. Importe todos os lançamentos que deverão ser considerados desse parque antes de fechar o plano. O histórico dos demais parques e eventuais ajustes manuais são preservados; inconsistências nessa transferência bloqueiam a importação.

## Otimização com estoque compartilhado

- **Este subparque, preservando os demais:** mantém as alocações dos outros parques e desconta suas reservas do saldo antes de otimizar o parque selecionado. Se os outros parques ainda não têm bobinas, use a opção de cálculo conjunto.
- **Todos os subparques:** permite redistribuir bobinas entre todos os trechos cadastrados, respeitando o estoque total.

O cálculo utiliza o solucionador existente: minimiza o objetivo ponderado de cortes, bobinas abertas e sobras pequenas, respeitando continuidade, cortes obrigatórios/proibidos, condutores compatíveis, bobinas fixadas e comprimentos disponíveis. Os pontos candidatos são as estruturas do traçado; o aplicativo não deduz locais fisicamente adequados para cortes apenas pela distância. As restrições de obra precisam ser informadas e conferidas.

O status distingue uma solução ótima para os pesos configurados de uma solução viável cujo ótimo não foi comprovado no tempo disponível. No modo por parque, a optimalidade é local, com as alocações dos outros parques mantidas. A metragem continua sendo calculada com distâncias lineares e acréscimos sem arredondar cada linha; o arredondamento ocorre uma vez por lançamento contínuo.

## Salvamento

O arquivo original fica associado aos lançamentos importados, com aba, intervalo, colunas e configuração. A seção **Referências salvas** permite baixar o original. Os arquivos são deduplicados pelo conteúdo e incluídos no mesmo SQLite e no backup JSON do projeto. Limite por arquivo: 10 MB; por aba: 30 mil linhas e 150 colunas. O armazenamento da hospedagem continua precisando ser persistente ou protegido por backups JSON.

Importar um controle completo ou substituir todos os trechos por CSV na página **Projeto e importação** substitui também as referências do projeto anterior. A importação por lançamento em **Subparques** preserva os demais dados.

## Verificação

Execute `python -m unittest discover -s tests -v`. A suíte cobre geração A/B/C, seleção de colunas, entradas inválidas, preservação de outros parques e níveis, reimportação sem duplicação, armazenamento do original, transição de histórico, estoque compartilhado e o fluxo da interface da prévia até a exportação do plano.
