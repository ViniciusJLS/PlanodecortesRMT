# Condutores e estruturas sem corte

## Atualizar o aplicativo

Integre esta alteração à branch main usada pelo Streamlit. Os lançamentos já salvos continuam disponíveis. Para reconhecer as restrições de uma referência importada antes desta versão, importe o Excel novamente e confira a prévia antes de substituir o lançamento.

## Importação AUX TRAMO

A distância L de uma linha corresponde ao poste I da linha anterior (De) até o poste I da linha atual (Para). Por exemplo, 88,49 m é o vão P.0/7D → P.0/5D. Não se usa a distância da linha De nem a distância de projeto arredondada.

Linhas com L = 0 representam postes inexistentes e são excluídas de DE/PARA. O primeiro vão positivo de cada tramo começa na SE (ou origem informada), usando L da linha desse primeiro poste válido. A partir dele, L segue medindo entre os postes válidos consecutivos. Marcadores P. e linhas vazias interrompem a sequência.

No campo **Origem dos tramos**, use SE ou a origem real do lançamento. Não é necessário informar distância para os postes de linha zero: eles não entram no traçado. As restrições azuis/1000-gaveta dessas linhas descartadas não são transferidas à SE.

## Estruturas sem corte

A importação mantém os vãos de distância positiva ligados a estruturas azuis ou de esforço 1000 posicionadas em GAVETA. Proíbe iniciar ou terminar um lançamento de bobina nessas estruturas. A restrição é vinculada ao poste, nas duas extremidades dos vãos adjacentes, e vale mesmo que o campo Corte no fim seja alterado para PERMITIDO.

São reconhecidas fontes e preenchimentos azuis nas colunas I:L, em RGB, cor indexada ou tema, além de esforço em J (ex.: 12/1000) e posição GAVETA em K. A prévia lista as estruturas reconhecidas. Cores que existam somente por formatação condicional não são avaliadas pelo importador; confira seus critérios antes do cálculo.

Se uma rota começar/terminar numa estrutura sem corte ou mudar de condutor nela, o sistema aponta a pendência. Inclua os vãos até uma estrutura onde o corte seja permitido. Não é criada uma solução que corte na estrutura restrita para atender à metragem de uma bobina.

## Cadastro de condutores

A página **Condutores** inclui o catálogo inicial extraído de **Dados Condutores(1).xlsx**, aba Dados: 36 registros subterrâneos e 26 aéreos. As descrições e propriedades técnicas são transcritas da fonte, sem corrigir valores ou calcular dimensionamento elétrico. Registros 2x permanecem identificados como na fonte; sua seleção não duplica automaticamente fases ou metragem.

Nesta página é possível cadastrar novos condutores por descrição/instalação ou importar uma versão atualizada do Excel no mesmo formato. O cadastro adicional pertence à obra ativa e é salvo com ela, inclusive no backup JSON. Reimportar atualiza as propriedades de descrições iguais na mesma instalação. O catálogo não cria bobinas de estoque.

Em **Subparques**, escolha o **Condutor padrão** antes de importar o lançamento. Para trechos já cadastrados, use **Selecionar condutor para vários trechos**, selecione os vãos e aplique o condutor. A seleção respeita a seção aérea/subterrânea e os filtros de circuito/nível. A alteração vale para A/B/C; também é possível editar cada fase individualmente no editor de trecho.

Bobinas/fixações incompatíveis com o novo condutor são liberadas apenas nos trechos alterados. Outros trechos e o estoque são preservados. Recalcule o plano depois de mudar os condutores. As descrições do trecho e da bobina precisam coincidir para a alocação.

O Excel final do subparque contém as bobinas calculadas, observações, critério de corte e restrição da estrutura. Só fica disponível para um plano atual validado.
