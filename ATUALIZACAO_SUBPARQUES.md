# Lançamentos por subparque

A página **Subparques** permite consultar, adicionar e editar os lançamentos de cada parque. Os registros salvos ficam no mesmo projeto e alimentam o **Resumo de bobinas**.

1. Selecione o subparque. Para trabalhar com todos, selecione as respectivas abas na importação do controle.
2. Consulte a **Rede aérea** e, abaixo dela, a **Rede subterrânea**. Ambas mantêm as fases A, B e C e os separadores duplos entre trechos.
3. Abra **Adicionar ou editar trecho** na seção desejada e selecione um trecho existente ou **Novo trecho**.
4. Escolha o circuito de **C01 a C34**, o nível **1, 2 ou 3**, as estruturas De/Para, a rota e a ordem. Preencha os dados e a bobina de cada fase.
5. Clique em **Salvar trecho e atualizar resumo** antes de trocar de trecho, subparque ou página. Alterações ainda não enviadas pelo formulário não estão salvas.
6. Use **Abrir Resumo de bobinas** para conferir a distribuição entre parques e os saldos.

Os filtros de circuito e nível apenas selecionam o que aparece na consulta. Os seletores dentro do formulário alteram os dados do trecho.

## Metragens e reservas

- Para os parques cadastrados/replanejados, o resumo usa os lançamentos salvos; valores importados desses mesmos parques são substituídos para evitar dupla contagem. Parques fora do cadastro mantêm o histórico importado.
- A soma usa as distâncias lineares sem arredondamento prévio, aplica as folgas e reservas cadastradas e arredonda uma vez por lançamento contínuo, por fase, circuito, nível, rota, tipo e bobina. Cortes obrigatórios e descontinuidades encerram o lançamento.
- A seção subterrânea contém quantidades de caixas, postes e turbinas e as respectivas sobras. As sobras são totais em metros, como no controle de referência, e não são multiplicadas novamente pelas quantidades.
- Projetos anteriores que possuem apenas a reserva agregada preservam essa metragem em **Outras reservas / legado**. A reimportação de um controle fornece o detalhamento disponível na planilha.
- Registros sem bobina não entram nos totais por bobina e são sinalizados no resumo. A metragem real da bobina substitui a redução de 3%; excedentes continuam destacados em vermelho.
- Um plano válido fornece suas próprias alocações ao resumo. Editar um trecho invalida o plano; as alocações dos outros trechos são preservadas no cadastro e os critérios precisam ser revisados antes de gerar um novo plano. Os lançamentos cadastrados não equivalem, por si só, a um plano validado.

## Salvamento e compatibilidade

Salvar um trecho atualiza somente aquele grupo de fases; os outros parques, níveis e tipos permanecem no projeto. Circuitos numéricos legados, como `7`, são padronizados para `C07` ao salvar, preservando a continuidade das rotas. As informações continuam no SQLite existente e no backup JSON. Em hospedagens com armazenamento temporário, mantenha os backups do projeto.

## Verificação

Execute `python -m unittest discover -s tests -v` na raiz do repositório. Os testes novos cobrem resumo sem dupla contagem, arredondamento, metragem real, edição atômica, rede subterrânea, banco de dados, troca entre subparques e navegação ao resumo. O teste da planilha original é opcional quando o arquivo de referência não está presente.
