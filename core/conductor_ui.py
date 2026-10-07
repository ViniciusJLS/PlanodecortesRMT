"""Cadastro e seleção de condutores por obra."""
import sqlite3
from zipfile import BadZipFile
import pandas as pd
import streamlit as st
from .conductors import catalog, options, register, parse_catalog, assign
from .reference_ui import persist


def render(project):
    if message:=st.session_state.pop('reference_message',None):st.success(message)
    st.caption('O catálogo inicial contém os condutores da referência fornecida. Novos cadastros e importações ficam salvos na obra ativa.')
    key=f"conductors_{project['id']}_{st.session_state.edit_version}"
    records=catalog(project)
    kind=st.selectbox('Instalação do catálogo',['Todos','AÉREO','SUBTERRÂNEO'],key=key+'_kind')
    shown=[{'Descrição':r['descricao'],'Instalação':r['tipo'],**r.get('dados',{}),'Origem':r.get('origem','')} for r in records if kind=='Todos' or r['tipo']==kind]
    st.dataframe(pd.DataFrame(shown).fillna('').astype(str),hide_index=True,width='stretch')
    st.caption('As propriedades são transcritas da referência. Escolher um condutor não calcula sua adequação elétrica. A bobina precisa ter a mesma descrição e instalação do trecho.')
    with st.expander('Cadastrar condutor na obra'):
        with st.form(key+'_new'):
            description=st.text_input('Descrição do novo condutor')
            installation=st.selectbox('Instalação do novo condutor',['AÉREO','SUBTERRÂNEO'])
            if st.form_submit_button('Salvar condutor'):
                try:
                    if any(r['descricao']==description.strip() and r['tipo']==installation for r in records):
                        raise ValueError('Este condutor já está cadastrado. Use a importação para atualizar suas propriedades.')
                    candidate=register(project,[dict(descricao=description,tipo=installation,dados={},origem='Cadastro manual')])
                    persist(project,candidate,'Condutor cadastrado nesta obra.')
                except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
    with st.expander('Importar ou atualizar catálogo pelo Excel'):
        uploaded=st.file_uploader('Excel de dados de condutores',type=['xlsx','xlsm'],key=key+'_upload')
        if uploaded:
            try:
                if uploaded.size>10*1024*1024:raise ValueError('Use um arquivo de até 10 MB.')
                rows=parse_catalog(uploaded.getvalue(),uploaded.name)
                st.write(f'{len(rows)} condutores reconhecidos. Descrições iguais no mesmo tipo serão atualizadas.')
                st.dataframe(pd.DataFrame(rows)[['descricao','tipo','origem']],hide_index=True,width='stretch')
                if st.button('Salvar catálogo nesta obra',key=key+'_import'):
                    persist(project,register(project,rows),'Catálogo salvo nesta obra.')
            except (ValueError,OSError,sqlite3.Error,BadZipFile) as exc:st.error(str(exc))


def selection(project,park,installation,groups,key):
    with st.expander('Selecionar condutor para vários trechos'):
        if not groups:return
        records=[next(r for r in g if not r.get('ausente')) for g in groups]
        def label(i):
            r=records[i]
            return f"{r['circuito']} · N{r['nivel']} · {r['de']} → {r['para']} · {r['rota']} · ordem {r['ordem']}"
        with st.form(key+'_conductors'):
            selected=st.multiselect('Trechos que receberão o condutor',list(range(len(groups))),format_func=label)
            description=st.selectbox('Condutor para os trechos selecionados',options(project,installation))
            st.caption('Aplica às fases A, B e C dos trechos escolhidos nesta seção. Bobinas incompatíveis serão liberadas para recalcular. Inclua os vãos adjacentes se houver uma estrutura sem corte na fronteira.')
            if st.form_submit_button('Aplicar condutor aos trechos'):
                try:
                    ids=[r['id'] for i in selected for r in groups[i] if not r.get('ausente')]
                    persist(project,assign(project,park,ids,description,installation),'Condutor aplicado. Recalcule as bobinas e o Excel final.')
                except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
