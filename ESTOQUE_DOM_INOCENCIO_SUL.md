# Cadastro do estoque Dom Inocêncio Sul

Esta atualização inclui o estoque extraído da aba RESUMO_BOBINAS de PLANO DE CORTE RMT - DOM INOCÊNCIO SUL 3(3).xlsx: 384 identificações únicas, sendo 369 aéreas e 15 subterrâneas.

Ao iniciar a versão atualizada, o aplicativo localiza a obra **Dom Inocêncio Sul** (ignorando acentos e diferenças de maiúsculas) ou a cria, se ainda não existir. Registra nela apenas as bobinas cujas identificações ainda não estão cadastradas. O estoque fica salvo no banco do aplicativo e disponível na página **Bobinas**.

## Como utilizar

1. Integre a PR à branch main usada pelo Streamlit.
2. Abra/recarregue o aplicativo atualizado.
3. Selecione **Dom Inocêncio Sul** em **Obra ativa**.
4. Abra **Bobinas** e confira a mensagem de cadastro e os registros.

O cadastro acontece uma única vez, com marcador salvo na obra. Edições posteriores, inclusive exclusões de bobinas, não são desfeitas ao recarregar. Outras obras, seus estoques e trechos são preservados. Se já houver obras homônimas, usa a obra ativa quando ela tem o nome solicitado; caso contrário, usa a homônima salva mais recentemente.

## Tratamento das metragens

Os comprimentos nominais vêm dos lances padrão da referência. A coluna BOBINA CHEIA, quando calculada com a redução contratual, não é usada como metragem real confirmada. O campo Real confirmada permanece vazio e a base disponível continua nominal × 97%, até uma confirmação do comprimento real pelo usuário.

O consumo anterior conserva a utilização histórica das bobinas por RSA01 a RSA09. Ao acrescentar uma bobina numa obra que já possui trechos de um desses parques, a parcela desse parque é retirada do consumo anterior uma vez e marcada como replanejada, seguindo a mesma regra do importador existente. Assim os trechos cadastrados passam a fornecer a utilização do parque, sem descontá-la duas vezes.

IDs existentes não têm seu nominal, real, histórico ou dados substituídos. Novas bobinas preservam romaneio, condutor, tipo e linha de origem. O cadastro não importa os trechos RSA nem cria bobinas fictícias.

Saldos negativos presentes na referência permanecem visíveis. Não há ajuste automático para zero nem alteração inventada da metragem real. Confira o histórico ou replaneje os parques correspondentes antes de otimizar. Inserir estoque invalida um plano anterior para que ele seja recalculado.

O JSON de referência contém apenas os dados necessários ao cadastro, com o nome e hash SHA-256 do arquivo de origem.
