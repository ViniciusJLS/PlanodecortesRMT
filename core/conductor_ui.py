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


def range_selection(project,park,installation,circuit,level,key):
    from .conductor_range import paths, interval_ids, apply_interval
    st.markdown('**Mudança de condutor**')
    try:
        routes=paths(project,park,installation,None if circuit=='Todos' else circuit,None if level=='Todos' else level)
    except ValueError as exc:
        st.error(str(exc));return
    if not routes:
        st.info('Cadastre os trechos para disponibilizar os postes das colunas DE e PARA.');return
    # Exact cell values, deduplicated in the order of the registered routes.
    posts=list(dict.fromkeys(node for route in routes for node in route['nodes']))
    a,b,c,d=st.columns([1.2,1.2,1.6,1])
    initial=a.selectbox('Poste inicial',[None]+posts,format_func=lambda v:v if v is not None else 'Selecione o poste',key=key+'_start')
    final=b.selectbox('Poste final',[None]+posts,format_func=lambda v:v if v is not None else 'Selecione o poste',key=key+'_end')
    description=c.selectbox('Condutor do intervalo',options(project,installation),key=key+'_conductor')
    phases=['A','B','C']
    with st.expander('Fases e prévia da mudança'):
        phases=st.multiselect('Fases do intervalo',['A','B','C'],default=phases,key=key+'_phases')
    matches=[]
    if initial is not None and final is not None and initial!=final:
        for route in routes:
            for start,node in enumerate(route['nodes']):
                if node!=initial:continue
                for end in range(start+1,len(route['nodes'])):
                    if route['nodes'][end]==final:matches.append((route,start,end))
    ids=[]
    selected_match=None
    if matches:
        if len(matches)>1:
            def label(i):
                route,start,end=matches[i];c,n,name,block=route['scope']
                return f"{c} · N{n} · {name} · bloco {block or 'principal'} · posições {start+1} a {end+1}"
            chosen=st.selectbox('Circuito, nível e rota deste intervalo',list(range(len(matches))),format_func=label,key=key+'_scope_'+str(initial)+'_'+str(final))
        else:chosen=0
        selected_match=matches[chosen]
        route,start,end=selected_match
        try:
            ids=interval_ids(project,park,installation,route,start,end,phases)
            st.caption(f'{end-start} vãos por fase · {len(ids)} registros. Opções de postes obtidas das células DE e PARA, respeitando os filtros da tabela.')
            with st.expander('Trechos que receberão o novo condutor'):
                selected=[r for r in project['trechos'] if r['id'] in set(ids)]
                st.dataframe(pd.DataFrame(selected)[['fase','de','para','condutor','linear']],hide_index=True,width='stretch')
        except ValueError as exc:st.warning(str(exc))
    elif initial is not None and final is not None:
        st.warning('Selecione postes distintos ligados por um intervalo contínuo no sentido DE → PARA da tabela.')
    else:
        st.caption('Escolha o poste inicial e o final nas listas das colunas DE e PARA. O vão após o poste final fica fora da mudança.')
    if d.button('Aplicar condutor',type='primary',disabled=not ids,key=key+'_apply'):
        try:
            route,start,end=selected_match
            candidate=apply_interval(project,park,installation,route,start,end,phases,description)
            persist(project,candidate,f'Condutor {description} aplicado de {initial} até {final}. Tabela atualizada; recalcule as bobinas.')
        except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
