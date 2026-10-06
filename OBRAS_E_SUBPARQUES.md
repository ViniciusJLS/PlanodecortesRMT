# Obras e subparques

A unidade de trabalho do aplicativo é a **obra**. Cada obra possui identificação própria e contém seus subparques, estoque de bobinas, trechos, referências Excel, critérios e plano de corte. Os projetos salvos anteriormente passam a aparecer como obras, sem conversão destrutiva nem cópia dos registros.

## Como usar

1. Abra **Obras** no menu lateral.
2. Preencha nome e código e clique em **Cadastrar e abrir obra**.
3. Confira o nome em **Obra ativa**, na barra lateral.
4. Abra **Subparques** e cadastre os parques pertencentes àquela obra.
5. Cadastre as bobinas e importe as referências de cada lançamento. Todas as operações, inclusive resumo e otimização conjunta dos subparques, ficam limitadas à obra ativa.
6. Salve os formulários antes de mudar de obra. Para trocar, use **Obra ativa** na barra lateral. Os dados já registrados na sessão são salvos; rascunhos ainda não enviados por formulários não são incorporados.
7. Use **Baixar backup da obra** para guardar um JSON com todos os dados da obra, inclusive suas referências Excel.

Subparques e bobinas podem ter o mesmo nome em obras diferentes. Cada obra é identificada por um ID exclusivo; o trecho desse ID mostrado no seletor também diferencia obras com nomes iguais. Não há compartilhamento automático de bobinas entre obras.

O nome da obra também pode ser alterado em **Projeto e importação**. Importar um controle completo substitui os dados somente da obra ativa e preserva seu nome cadastrado. A restauração de backup cria uma nova obra com outro ID; duplicar uma obra também produz um cadastro independente.

Ao iniciar uma nova sessão, o aplicativo abre a obra salva mais recentemente. Se ainda não houver obra salva, apresenta a demonstração. Ao trocar de obra, os editores, uploads e filtros da anterior são limpos da interface para impedir que sejam aplicados na obra seguinte. Os arquivos e configurações já salvos permanecem no cadastro da respectiva obra.

O isolamento é dos dados de planejamento, não uma separação de contas/permissões. O aplicativo continua usando SQLite no servidor e o uso individual já previsto. Em hospedagem com armazenamento temporário, mantenha os backups JSON das obras.

## Validação

Os testes verificam obras com subparques e bobinas de nomes iguais, preservação de referências, restauração independente de backup, cadastro e troca pela interface e limpeza dos controles da obra anterior. Execute `python -m unittest discover -s tests -v`.
