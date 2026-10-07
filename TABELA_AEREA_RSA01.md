# Tabela aérea no padrão RSA-01

A consulta de rede aérea na página Subparques segue a estrutura da aba RSA-01 da referência PLANO DE CORTE RMT - DOM INOCÊNCIO SUL 3(3).xlsx.

Colunas, na ordem da referência:

1. DESCRIÇÃO (NIVEL 1)
2. BOBINA (NIVEL 1)
3. CIRCUITO (NIVEL 1)
4. DESCRIÇÃO (NIVEL 2)
5. BOBINA (NIVEL 2)
6. CIRCUITO (NIVEL 2)
7. FASE
8. TIPO
9. DE
10. PARA
11. DISTÂNCIA PROJETO
12. SOBRA BOBINA 1
13. SOBRA BOBINA 2
14. OBSERVAÇÕES

As colunas L a S do Excel não aparecem na tabela aérea: DISTÂNCIA LINEAR, FOLGA DESNÍVEL, QTE. CAIXAS, SOBRA CAIXA, QTE. POSTE, SOBRA POSTE, QTE. TURBINA e SOBRA SAÍDA TURBINA. Seus dados permanecem no cadastro e nos cálculos.

Níveis de um mesmo vão, ordem e rota são apresentados lado a lado. Cada grupo tem as fases A, B e C, com separador duplo depois de C. Circuitos adicionais no mesmo nível ficam em grupos separados. Os filtros de circuito e nível continuam sendo aplicados antes da montagem da tabela; células de níveis fora do filtro ficam vazias.

Quando há lançamentos no nível 3, a tabela acrescenta DESCRIÇÃO, BOBINA e CIRCUITO (NIVEL 3) e SOBRA BOBINA 3, para que esses dados continuem visíveis.

DISTÂNCIA PROJETO apresenta a necessidade do vão com folga e reserva, sem arredondar cada linha. Se os níveis têm necessidades diferentes, os valores ficam identificados como N1, N2 e N3 na mesma célula. O plano mantém o arredondamento único por lançamento contínuo já usado pelo aplicativo.

SOBRA BOBINA indica o saldo na obra depois do consumo anterior e dos lançamentos de todos os subparques. Um plano atual fornece as bobinas calculadas; na ausência dele, a consulta considera as bobinas já cadastradas nos trechos. Bobinas ausentes ou valores pendentes aparecem como —.

Restrições de estrutura e cortes proibidos continuam visíveis em OBSERVAÇÕES. A edição de trechos e a seleção de condutores preservam seus controles atuais.

Esta alteração aplica-se à tabela de consulta aérea. A seção subterrânea mantém suas colunas de reservas, caixas, postes e turbinas.
