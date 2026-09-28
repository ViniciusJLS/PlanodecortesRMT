# RMT — Plano de corte

Aplicação Streamlit para planejar lançamentos de cabos de média tensão, controlar
bobinas e gerar dois documentos Excel a partir do mesmo resultado validado.

## Abrir no Windows

1. Instale Python 3.11 ou 3.12, caso ainda não tenha.
2. Extraia todo o ZIP para uma pasta.
3. Execute `INICIAR_WINDOWS.bat`. A primeira execução instala as dependências e
   precisa de internet.
4. A aplicação abre no navegador. Caso não abra automaticamente, acesse
   `http://localhost:8501`.

Mantenha a janela do terminal aberta durante o uso. Para encerrar, pressione
Ctrl+C no terminal. Os dados salvos ficam em `data/projetos.sqlite3`.

Alternativa no terminal, a partir da pasta extraída:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Primeira utilização

A tela inicial usa dados fictícios identificados como demonstração. Para testar
o fluxo, abra **Plano e entregáveis** e clique em **Gerar plano de corte**.

Para usar os dados enviados nesta conversa:

1. Abra **Projeto e importação**.
2. Marque **Usar a planilha de controle enviada nesta conversa**, ou envie outro
   arquivo do mesmo modelo.
3. Selecione os parques a replanejar e clique em **Importar parques selecionados**.
4. Confira os registros de **Traçado** e **Bobinas**, especialmente avisos e
   consumos anteriores. Cada fase e nível corresponde a um condutor separado.
5. Na tela **Critérios de corte**, configure as travessias, folgas e prioridades.
   Confirme a revisão dos critérios após verificar amarrações e pontos de corte.
6. Gere uma nova alocação ou consolide as bobinas já atribuídas na planilha.
7. Revise os lançamentos, ajuste bobinas se necessário e baixe os dois Excel.

O arquivo `referencias/controle_original.xlsx` é uma cópia sem alteração da
planilha enviada. `referencias/entregavel_referencia.xlsx` é o documento de
referência original. Eles não são necessários para usar CSV ou cadastrar novos
projetos. Não publique essas planilhas em um repositório público; a configuração
de Git já as exclui.

## Regras implementadas

- Se a metragem real da bobina estiver preenchida, ela é a base disponível.
  Caso contrário, a base é o nominal multiplicado por 0,97. Zero informado é
  tratado como zero real, e não como um campo vazio.
- Saldo = base − consumo anterior − reserva do plano atual.
- Gerar outra simulação substitui a reserva do plano, sem duplicar o desconto.
- Na importação, consumos dos parques selecionados são retirados do histórico
  porque serão replanejados. Os demais parques permanecem como consumo anterior.
  Não selecione como replanejamento um parque já executado sem verificar o escopo.
- O importador reconhece os cabeçalhos de cada bloco e os limites das tabelas
  do Excel. Não considera anotações soltas fora das tabelas como novos trechos.
- O arquivo original tem distâncias de vão ré. A aplicação importa as relações
  **DE/PARA e DISTÂNCIA LINEAR já estabelecidas nas abas RSA**, sem reinterpretar
  a aba TRAMO. Uma importação exclusiva da aba TRAMO ainda não foi implementada.
- Um lançamento contém trechos consecutivos da mesma rota, parque, circuito,
  nível, fase, condutor e tipo, alocados à mesma bobina.
- Distância de projeto = teto da soma de `linear × (1 + folga) + reserva` dos
  trechos do lançamento. Quando a folga é uniforme, equivale a aplicar o
  percentual sobre a distância linear consolidada. O arredondamento acontece
  somente no final do lançamento.
- As reservas devem ser cadastradas uma única vez por ocorrência física e por
  condutor. O programa mantém as reservas informadas; não deduz automaticamente
  se a mesma caixa ou terminal foi lançado duas vezes.
- Um corte obrigatório encerra o lançamento. Um corte proibido impede seu
  término naquele ponto. Uma travessia aplica proibições nos pontos intermediários;
  suas extremidades preservam os critérios existentes.
- A marca `TRAV` do legado aparece como observação e precisa de delimitação pelo
  usuário. Não se presume que todos os postes aceitam cortes.
- O algoritmo não introduz emendas dentro de um trecho elementar.
- Um campo **Bobina fixada** preserva a escolha nas próximas otimizações.
- Trocar uma bobina manualmente exige auditoria de compatibilidade, saldo,
  continuidade, cobertura e restrições.
- Informar a metragem real posteriormente revalida o plano; se ele não couber,
  o resultado é invalidado. Um plano revalidado não é declarado ótimo novamente.
- Sobras abaixo do limite são sinalizadas, sem baixa automática como descarte.

## Otimização

O motor gera possibilidades de cortes contínuos e resolve conjuntamente a
escolha dos cortes e sua distribuição nas bobinas usando OR-Tools CP-SAT.
O atendimento integral dos trechos é obrigatório. O objetivo ponderado é:

```
peso_cortes × quantidade_de_cortes
+ peso_bobinas × bobinas_utilizadas
+ peso_perda × metros_de_sobra_abaixo_do_limite
```

Os pesos são editáveis. Não há promessa de ótimo absoluto para todos os
possíveis objetivos de obra. A interface diferencia solução comprovadamente
ótima para esses pesos de uma solução viável obtida dentro do prazo.
O modo rápido encerra na primeira solução viável.

O limite configurado vale para o solucionador; a geração de combinações pode
acrescentar tempo. Existe uma proteção de 180 mil combinações para evitar
modelos excessivamente grandes. Divida o planejamento por escopo ou fixe as
escolhas consolidadas quando esse limite for alcançado.

Se houver falta de capacidade ou restrições incompatíveis, nenhum entregável
parcial é liberado como plano completo. Quando o tempo termina sem solução,
a mensagem não afirma que a situação é inviável.

## Exportações

**Controle_RMT.xlsx:** resumo, trechos elementares, lançamentos, estoque e critérios.

**Plano_de_Corte_RMT.xlsx:** resumo das bobinas usadas no documento, lançamentos
por parque/circuito/tipo e critérios. Inclui condutor, bobina, circuito, fase,
nível, de, para, distância linear, acréscimos e distância de projeto.

Os arquivos são instantâneos numéricos do plano validado. Para alterar cálculos,
edite o projeto e exporte novamente. O layout é próprio, com cabeçalhos, filtros,
painéis congelados e configuração de impressão. Reproduz os campos do modelo,
mas não o desenho gráfico exato da capa, assinaturas ou logotipos corporativos.
O status é de planejamento; não se copia uma aprovação do documento original.

## Pendências encontradas na planilha de referência

Na leitura de RSA-12 foram importados **522 registros de condutores** e **384
registros de bobinas**. A validação básica encontrou **69 pendências**: um
problema de identificação repetida no estoque (`EDIV-400-001`) e 68 registros
com consumo externo ao escopo maior que a base contratual considerada.

Esses registros são preservados para revisão. Não foi aumentada a metragem
real, zerado um saldo ou removida uma bobina para forçar um resultado. Confirme
as metragens entregues e o consumo histórico antes de planejar esse caso real.

## Projetos e persistência

Salvar grava o projeto em SQLite; uma nova simulação não baixa cabo executado.
O consumo de execução deve ser atualizado no cadastro de bobinas ou por uma
nova importação. Esta versão não é um sistema multiusuário de almoxarifado.
Dois projetos independentes podem reservar a mesma bobina: concilie o estoque
antes de executar planos paralelos. Para uma alocação global, use um único
projeto com todos os parques que participarão do mesmo planejamento.

O botão de backup exporta JSON. Restaurar cria um novo projeto e requer nova
validação do plano. Para escolher outro local do banco, configure a variável
de ambiente `RMT_DB_PATH`.

## Publicar no Streamlit

O código está preparado para o Streamlit Community Cloud, mas não foi publicado
em uma conta do usuário durante esta entrega.

1. Suba `app.py`, `core/`, `.streamlit/config.toml` e `requirements.txt` para um
   repositório GitHub. Não suba o banco de dados nem as referências da obra.
2. No Streamlit Community Cloud, escolha **Create app**.
3. Selecione o repositório, a branch e `app.py` como arquivo principal.
4. Use Python 3.12 e conclua a publicação.
5. Importe suas planilhas pela aplicação após abrir o endereço publicado.

Documentação oficial consultada:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

Em hospedagens com armazenamento temporário, o SQLite pode ser perdido após
reinício ou nova implantação. Faça backup JSON ou hospede com volume persistente.
Esta versão é para uso individual/confiável e não implementa autenticação própria
ou isolamento entre usuários. Não a exponha como serviço público de múltiplos
usuários com dados de obra sem implementar essas funções.

## Verificação e estrutura

```bash
python -m unittest discover -s tests -v
```

Os testes verificam tolerância contratual versus metragem real, arredondamento,
saldo, continuidade, cortes obrigatórios/proibidos, alocações fixadas, importação
com colunas alternadas, arquivos Excel e navegação/cálculo pela interface.

```
app.py                 Interface e fluxo de trabalho
core/engine.py         Cálculo, otimização e auditoria
core/importer.py       Excel legado e CSV normalizado
core/exporter.py       Dois documentos XLSX em OOXML
core/project.py        Projetos, demonstração e SQLite
tests/                 Testes de regras e interface
referencias/           Cópias dos arquivos enviados
```
