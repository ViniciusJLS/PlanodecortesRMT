# Plano de Cortes RMT ⚡

Aplicação web para planejar o lançamento de cabos de **Rede de Média Tensão (RMT)**, distribuir bobinas entre trechos e acompanhar o estoque por obra e subparque.

O sistema reúne o traçado, as características dos condutores, as metragens das bobinas e os critérios de corte para gerar um plano de lançamento com rastreabilidade e exportação em Excel.

**[Acessar o aplicativo](https://planodecortesrmt-2zzywsz2q99xdjtybmfnqn.streamlit.app/)** · **[Repositório](https://github.com/ViniciusJLS/PlanodecortesRMT)**

## 📋 Descrição do projeto

O Plano de Cortes RMT foi desenvolvido para apoiar o planejamento de lançamentos de cabos em parques. A interface permite cadastrar obras independentes, organizar seus subparques e importar planilhas de referência para formar os trechos **DE → PARA**, com distância linear, circuito, nível, fase e condutor.

A partir desses dados, o aplicativo procura alocar as bobinas de forma contínua, respeitando sua capacidade e os pontos permitidos de corte. O resultado pode ser conferido na tela, ajustado e exportado para os documentos de controle e de entrega.

## 🎯 Objetivo

Melhorar o aproveitamento das bobinas considerando também a execução em campo: reduzir interrupções de lançamento, evitar sobras pouco úteis e favorecer o compartilhamento entre subparques próximos.

O planejamento considera as fases **A, B e C** separadamente. A metragem de cabo soma fases e níveis; portanto, não representa apenas a extensão geográfica da rede.

## 🚀 Como funciona

1. **Cadastro da obra:** organize os subparques e o estoque de bobinas da obra selecionada.
2. **Importação do traçado:** envie o Excel de referência e confira os postes, as distâncias e os trechos reconhecidos.
3. **Definição dos condutores:** selecione circuito, nível, instalação e condutor. Na página Subparques, também é possível alterar o condutor entre um poste inicial e um poste final das colunas DE/PARA.
4. **Configuração dos critérios:** revise cortes permitidos, proibidos e obrigatórios, travessias, folgas, reservas e preferências operacionais.
5. **Cálculo do plano:** o motor escolhe bobinas e lançamentos contínuos, verificando atendimento dos trechos e balanço de material.
6. **Conferência e entrega:** visualize os lançamentos, consulte o resumo das bobinas e baixe os arquivos Excel.

## ✨ Funcionalidades

- Cadastro de obras e subparques com dados separados por obra.
- Importação de controle Excel, referência por subparque e CSV no formato suportado.
- Leitura do formato AUX TRAMO, com postes na coluna I e distâncias na coluna L da aba PLANO DE CORTE.
- Tabelas de rede aérea e subterrânea, com registros por fase e separação visual dos trechos.
- Seleção de circuitos de **C01 a C34** e níveis **1, 2 e 3**.
- Catálogo de condutores e aplicação de condutor por intervalo de postes.
- Cadastro de bobinas com comprimento nominal, metragem real e consumo anterior.
- Resumo das bobinas utilizadas, parques atendidos, consumo e saldo disponível.
- Gráficos de utilização por subparque e totais de bobinas e comprimento por condutor.
- Critérios operacionais de continuidade, sobras, operações curtas e proximidade entre parques.
- Identificação de estruturas sem corte por marcação azul ou esforço 1000 em gaveta, conforme a referência reconhecida.
- Ajuste manual de bobinas com revalidação do plano.
- Exportação do controle, do entregável e do Excel final de cada subparque.
- Backup da obra em JSON e restauração como nova obra.

## 🧮 Regras de planejamento

### Capacidade das bobinas

Quando a metragem real está informada, ela substitui a estimativa contratual. Na ausência dessa informação, novos lançamentos usam **97% do comprimento nominal**.

```text
Base da bobina = metragem real informada ou nominal × 0,97
Saldo para planejamento = base − consumo anterior − reserva do plano atual
```

Um consumo histórico acima dos 97%, mas dentro do nominal e sem metragem real confirmada, recebe um aviso de conferência. Esse caso não aumenta a capacidade para novos cortes: a bobina sem saldo conservador fica indisponível para novas alocações até a confirmação da metragem.

### Distâncias e continuidade

A distância de projeto de um lançamento é calculada a partir das **distâncias lineares dos trechos**, das folgas e das reservas cadastradas. O arredondamento para cima ocorre uma única vez por lançamento contínuo; não se somam distâncias de projeto já arredondadas por linha.

```text
Comprimento de corte = arredondar para cima a soma de:
linear × (1 + folga) + reserva
```

O lançamento deve manter continuidade DE → PARA e compatibilidade de obra, subparque, circuito, nível, fase, condutor, instalação e rota. O sistema não permite cortes intermediários em estruturas classificadas como sem corte.

### Prioridades operacionais

A otimização resolve as prioridades em sequência, preservando o resultado obtido nas etapas anteriores:

1. Reduzir a quantidade de lançamentos contínuos.
2. Preferir bobinas consumidas em um único lançamento, com sobra tolerada.
3. Evitar sobras intermediárias e lançamentos curtos.
4. Preferir o compartilhamento entre parques próximos.
5. Desempatar pela metragem de estoque mobilizada.

Os limites iniciais são ajustáveis por obra: sobra tolerada até **60 m**, sobra intermediária acima de **60 m até 500 m**, sobra reutilizável acima de **500 m** e lançamento curto até **500 m**. A proximidade física e a ordem de execução são informadas pelo usuário; não são deduzidas da numeração dos parques.

A interface distingue uma solução viável de uma solução com ótimo comprovado para as prioridades configuradas. Os indicadores operacionais não estimam custo em reais ou horas de equipe.

> **Atualização do AUX TRAMO:** a exclusão dos postes de linhas com L = 0, com início dos tramos na SE e correção de referências já importadas, está proposta na [PR #16](https://github.com/ViniciusJLS/PlanodecortesRMT/pull/16). Verifique a incorporação dessa atualização antes de usar essa interpretação das linhas zero.

## 🛠️ Tecnologias utilizadas

| Tecnologia | Uso no projeto |
|---|---|
| Python | Regras de negócio, importação, cálculos e exportação |
| Streamlit | Interface web e fluxo de trabalho |
| OR-Tools CP-SAT | Otimização das alocações e dos cortes |
| pandas | Organização e apresentação dos dados |
| openpyxl | Leitura e inspeção dos arquivos Excel |
| Altair | Gráficos interativos da Visão Geral |
| SQLite | Armazenamento local das obras |

## 💻 Instalação e execução local

Use Python **3.12**, Git e acesso à internet para instalar as dependências.

### 1. Clone o repositório

```bash
git clone https://github.com/ViniciusJLS/PlanodecortesRMT.git
cd PlanodecortesRMT
```

### 2. Crie o ambiente virtual

```bash
python -m venv .venv
```

Ative no Windows, pelo Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

Ou no Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
python -m pip install -r requirements.txt
```

### 4. Inicie o aplicativo

```bash
python -m streamlit run app.py
```

Abra **http://localhost:8501** no navegador. Mantenha o terminal aberto durante o uso e pressione **Ctrl+C** para encerrar.

## 🧭 Páginas do aplicativo

| Página | Finalidade |
|---|---|
| Visão geral | Indicadores, gráficos e lançamentos do plano |
| Obras | Cadastro e seleção da obra ativa |
| Projeto e importação | Identificação da obra, importações e restauração de backup |
| Subparques | Referências, tabelas de lançamento, condutores por intervalo e cálculo |
| Condutores | Consulta, cadastro e importação do catálogo |
| Traçado | Edição dos trechos e dos critérios pontuais de corte |
| Resumo de bobinas | Consumo e saldo por bobina e subparque |
| Bobinas | Cadastro e atualização das metragens do estoque |
| Critérios de corte | Restrições físicas e preferências operacionais |
| Plano e entregáveis | Cálculo, auditoria, ajustes e exportações |

## 📦 Arquivos de saída

- **Controle_RMT.xlsx:** trechos, lançamentos, resumo, estoque e critérios do plano.
- **Plano_de_Corte_RMT.xlsx:** entregável com lançamentos contínuos e resumo das bobinas utilizadas.
- **Plano_de_Corte_<subparque>.xlsx:** Excel final do subparque, com trechos e bobinas alocadas.
- **Backup JSON:** dados da obra para restauração posterior.

Os arquivos Excel são um retrato do resultado validado. Após alterar o traçado, as metragens ou os critérios, recalcule e exporte novamente.

## 👩‍💻 Estrutura do projeto

| Caminho | Responsabilidade |
|---|---|
| `app.py` | Navegação e interface principal |
| `core/engine.py` | Cálculo, otimização e auditoria dos lançamentos |
| `core/operations.py` | Prioridades operacionais e indicadores |
| `core/project.py` | Cadastro das obras e persistência em SQLite |
| `core/importer.py` | Importação de controle e CSV |
| `core/reference.py` | Referências e planejamento por subparque |
| `core/tramo.py` | Conversão do AUX TRAMO e reconhecimento de restrições |
| `core/conductor_range.py` | Seleção contínua entre postes para alterar o condutor |
| `core/inventory.py` | Resumo de consumo e saldo das bobinas |
| `core/overview.py` | Dados e gráficos da Visão Geral |
| `core/exporter.py` | Geração dos documentos Excel |
| `tests/` | Testes das regras e da interface |
| `requirements.txt` | Dependências do aplicativo |

## 🧪 Verificação

Com o ambiente virtual ativo e as dependências instaladas, execute:

```bash
python -m unittest discover -s tests -v
```

A suíte cobre importações, continuidade, estoque, arredondamento, estruturas sem corte, condutores por intervalo, separação entre obras, exportação e fluxos da interface. Alguns testes que dependem de referências privadas podem ser ignorados quando esses arquivos não estiverem disponíveis.

## 💾 Dados e backup

O banco padrão é criado em `data/projetos.sqlite3`. Para escolher outro local, configure a variável de ambiente `RMT_DB_PATH` antes de iniciar o aplicativo.

Use **Baixar backup da obra**, na barra lateral, para guardar o JSON. Em ambientes com disco temporário, reinícios ou novas implantações podem perder o banco local. As obras são separadas no cadastro, mas o aplicativo não implementa autenticação própria nem gestão de estoque multiusuário.

As metragens calculadas representam reservas de planejamento. A execução e o consumo efetivo devem ser registrados e conferidos no estoque.

## 📚 Documentação complementar

- [Obras e subparques](OBRAS_E_SUBPARQUES.md)
- [Referências por subparque](REFERENCIAS_POR_SUBPARQUE.md)
- [Formato AUX TRAMO e Excel final](AUX_TRAMO_E_EXCEL_FINAL.md)
- [Condutores e estruturas sem corte](CONDUTORES_E_ESTRUTURAS_SEM_CORTE.md)
- [Critérios operacionais](CRITERIOS_OPERACIONAIS.md)
- [Tabela aérea no padrão RSA-01](TABELA_AEREA_RSA01.md)

## 🤝 Responsável pelo projeto

Mantido por **[Vinicius Silva](https://github.com/ViniciusJLS)**.

Para relatar um problema, abra uma [issue](https://github.com/ViniciusJLS/PlanodecortesRMT/issues) com a mensagem exibida, o passo a passo e um exemplo sem dados confidenciais.

A organização deste README foi inspirada no [Sentiment Analyzer Streamlit](https://github.com/ArthurGalvincio/sentiment-analyzer-streamlit), com conteúdo adaptado ao planejamento de bobinas de RMT.
