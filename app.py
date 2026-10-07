from pathlib import Path
import copy
import io
import json
import uuid
import pandas as pd
import streamlit as st
from core import engine, importer, project as projects
from core.exporter import export
from core.inventory import summarize, row_style
from core.subpark_ui import render as render_subparks
from core.conductor_ui import render as render_conductors
from core.initial_stock import ensure_stock, MIGRATION

st.set_page_config(page_title='RMT · Plano de corte', page_icon='⚡', layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:#f4f7fb;color:#182c42}h1{font-size:2rem!important;font-weight:700!important;letter-spacing:-.04em}h2{font-size:1.3rem!important}
[data-testid="stSidebar"]{background:#12283f;}[data-testid="stSidebar"] *{color:#edf4fa}
[data-testid="stSidebar"] input{color:#182c42}[data-testid="stSidebar"] button p{color:#182c42}
[data-testid="stMetric"]{background:white;border:1px solid #dce5ee;border-radius:10px;padding:16px 20px;}
[data-testid="stMetricLabel"]{color:#5d7185;font-size:.9rem}[data-testid="stMetricValue"]{font-size:1.8rem}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1580px}
.eyebrow{color:#047d83;font-size:.8rem;font-weight:700;letter-spacing:.14em;margin-bottom:.4rem}
.topline{display:flex;align-items:center;gap:.6rem}.brand{font-size:1.55rem;font-weight:700;letter-spacing:.12em}
[data-testid="stDataFrame"]{border:1px solid #dce5ee;border-radius:8px}
div.stButton>button[kind="primary"]{background:#087e83;border-color:#087e83}
</style>''', unsafe_allow_html=True)

if 'project' not in st.session_state:
    saved = projects.saved_projects()
    st.session_state.project = projects.load(saved[0][0]) if saved else projects.demo()
    st.session_state.edit_version = 0

p = st.session_state.project

seeded_work,seeded_count=ensure_stock(p)
if seeded_work['id']==p['id'] and seeded_work is not p:
    st.session_state.project=seeded_work
    st.session_state.edit_version+=1
    p=seeded_work


def fmt(v):
    return f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def commit(clear_plan=True):
    if clear_plan:
        p['plano'] = None
    projects.save(p)
    st.session_state.edit_version += 1


def activate_work(value):
    current = st.session_state.project
    if current['id'] != value['id']:
        projects.save(current)
    projects.save(value)
    # Remove editores, uploads e filtros da obra anterior, mantendo apenas a navegação.
    for key in list(st.session_state):
        if key not in ('project', 'edit_version', 'work_area'):
            del st.session_state[key]
    st.session_state.project = value
    st.session_state.edit_version += 1


def choose_work():
    target = st.session_state.obra_ativa
    if target != st.session_state.project['id']:
        activate_work(projects.load(target))


def switch_project(value):
    activate_work(value)
    st.rerun()


def records(df):
    return json.loads(df.to_json(orient='records', force_ascii=False))


def show_issues(errors):
    if errors:
        st.error(f'{len(errors)} pendência(s) impedem o cálculo.')
        st.dataframe(pd.DataFrame({'Pendência':errors}), hide_index=True, width='stretch')
    else:
        st.success('Dados básicos consistentes. A viabilidade dos cortes será verificada na alocação.')


with st.sidebar:
    st.markdown('<div class="brand">⚡ RMT</div>', unsafe_allow_html=True)
    st.caption('PLANEJAMENTO DE CABOS')
    works = {ident:name for ident,name,_ in projects.saved_projects()}
    works[p['id']] = p['nome']
    work_ids = sorted(works, key=lambda ident:(works[ident].casefold(),ident))
    if st.session_state.get('obra_ativa') != p['id']:
        st.session_state.obra_ativa = p['id']
    st.selectbox('Obra ativa', work_ids,
        format_func=lambda ident:f'{works[ident]} · {ident[:8]}', key='obra_ativa', on_change=choose_work)
    st.caption('Salve os formulários antes de trocar de obra. Cada obra mantém seus próprios subparques, estoque e plano.')
    st.divider()
    page = st.radio('Área de trabalho', ['Visão geral','Obras','Projeto e importação','Subparques','Condutores','Traçado','Resumo de bobinas','Bobinas','Critérios de corte','Plano e entregáveis'], label_visibility='collapsed', key='work_area')
    st.divider()
    st.markdown(f"**{p['nome']}**")
    st.caption(f"Revisão {p['revisao']} · {len(p['trechos'])} trechos")
    if st.button('Salvar obra', width='stretch'):
        projects.save(p)
        st.toast('Projeto salvo neste servidor.')
    st.download_button('Baixar backup da obra', json.dumps(p, ensure_ascii=False, indent=2),
                       file_name=f"obra_rmt_{p['id'][:8]}.json", mime='application/json', width='stretch')
    st.caption('Os planos reservam metragem. O consumo executado é registrado separadamente no cadastro das bobinas.')

st.markdown('<div class="eyebrow">ENGENHARIA · REDE DE MÉDIA TENSÃO</div>', unsafe_allow_html=True)
st.title(page)
st.caption(f"Obra ativa: {p['nome']}")

if page == 'Obras':
    st.write('Cadastre a obra e depois seus subparques. Todas as páginas trabalham exclusivamente com a obra selecionada na barra lateral.')
    with st.form('create_work'):
        a,b = st.columns([2,1])
        work_name = a.text_input('Nome da obra', placeholder='Ex.: Dom Inocêncio Sul')
        work_code = b.text_input('Código da obra / documento', value='PLANO-RMT')
        if st.form_submit_button('Cadastrar e abrir obra', type='primary'):
            try:
                created = projects.create_work(work_name, work_code)
                switch_project(created)
            except ValueError as exc:
                st.error(str(exc))
    st.subheader('Obras cadastradas')
    catalog = []
    for ident,name,updated in projects.saved_projects():
        work = p if ident == p['id'] else projects.load(ident)
        subparks = set(work.get('subparques',[])) | {r['parque'] for r in work['trechos']}
        catalog.append({'Obra':work['nome'],'Identificação':ident[:8], 'Subparques':len(subparks),
                        'Registros de fase':len(work['trechos']), 'Bobinas':len(work['bobinas']),
                        'Atualizada':updated[:16], 'Ativa':ident==p['id']})
    if catalog:
        st.dataframe(pd.DataFrame(catalog), hide_index=True, width='stretch')
    else:
        st.info('Cadastre a primeira obra. A demonstração atual só entra no cadastro quando for salva ou ao trocar de obra.')
    st.caption('Os projetos salvos anteriormente já aparecem como obras, preservando os dados. Obras podem ter subparques e bobinas com os mesmos nomes; cada cadastro fica isolado pelo identificador da obra.')

elif page == 'Visão geral':
    st.caption('Do traçado ao lançamento contínuo, com rastreabilidade de cada bobina.')
    if p['nome'] == 'Parque demonstração':
        st.info('Você está no exemplo demonstrativo. Importe seu controle em “Projeto e importação” para trabalhar com dados reais.')
    cuts = (p.get('plano') or {}).get('cortes', [])
    try:
        inv = engine.stock(p, cuts)
    except (ValueError, TypeError, ArithmeticError, KeyError):
        inv = []
        st.warning('Há metragens incompletas no cadastro. Confira a tela Bobinas antes de calcular os saldos.')
    a,b,c,d = st.columns(4)
    a.metric('Trechos por condutor',len(p['trechos']))
    b.metric('Bobinas cadastradas',len(p['bobinas']))
    c.metric('Cabo reservado',fmt(sum(c['projeto'] for c in cuts))+' m')
    d.metric('Saldo após o plano',fmt(sum(r['saldo'] for r in inv))+' m')
    st.write('')
    left,right = st.columns([1.8,1])
    with left:
        st.subheader('Disponibilidade por condutor')
        if inv:
            df = pd.DataFrame(inv).groupby('condutor')[['reservado','saldo']].sum()
            st.bar_chart(df.rename(columns={'reservado':'Reservado','saldo':'Saldo'}), color=['#0c858a','#8fa7bf'], horizontal=True)
        else:
            st.info('Cadastre as bobinas para visualizar o estoque.')
    with right:
        st.subheader('Preparação do plano')
        checks = [('Traçado cadastrado', bool(p['trechos'])), ('Estoque cadastrado',bool(p['bobinas'])),
                  ('Critérios revisados',p.get('criterios_confirmados',False)), ('Plano validado',bool(cuts))]
        for label, done in checks:
            st.write(('✓ ' if done else '○ ') + label)
        if cuts:
            st.success(p['plano']['status'])
        st.caption('A metragem da rede é diferente da metragem de cabo: fases e níveis são contabilizados separadamente.')
    st.subheader('Lançamentos do plano')
    if cuts:
        st.dataframe(pd.DataFrame(cuts).drop(columns='trechos'), hide_index=True, width='stretch')
    else:
        st.info('Revise os critérios e gere o primeiro plano na tela “Plano e entregáveis”.')

elif page == 'Projeto e importação':
    with st.form('metadata'):
        a,b,c = st.columns([2,1,1])
        name = a.text_input('Nome da obra',p['nome'])
        code = b.text_input('Código do documento',p['codigo'])
        revision = c.text_input('Revisão',p['revisao'])
        if st.form_submit_button('Salvar identificação', type='primary'):
            p.update(nome=name,codigo=code,revisao=revision)
            commit(False)
            st.success('Identificação salva.')
    tabs = st.tabs(['Importar controle Excel','Importar CSV','Projetos salvos'])
    with tabs[0]:
        st.write('Selecione os parques que serão replanejados. O consumo dos demais parques permanece descontado do estoque.')
        uploaded = st.file_uploader('Controle de bobinas e trechos', type=['xlsx'])
        ref = Path(__file__).parent/'referencias'/'controle_original.xlsx'
        use_ref = st.checkbox('Usar a planilha de controle enviada nesta conversa',value=False) if ref.exists() else False
        content = uploaded.getvalue() if uploaded else (ref.read_bytes() if use_ref else None)
        if content:
            try:
                parks = importer.list_parks(content)
                selected = st.multiselect('Parques para replanejar',parks,default=['RSA-12'] if 'RSA-12' in parks else parks[:1])
                st.warning('A importação substitui os trechos e o estoque do projeto aberto. Baixe um backup para manter a versão anterior.')
                if st.button('Importar parques selecionados',type='primary',disabled=not selected):
                    with st.spinner('Lendo cabeçalhos e metragens…'):
                        rows,reels,warnings = importer.import_control(content,selected)
                    p.update(trechos=rows,bobinas=reels,avisos=warnings,criterios_confirmados=False,
                             subparques=selected,referencias_subparques={},arquivos_referencia={})
                    if p['nome'] in ('Parque demonstração','Novo projeto','Nova obra'):
                        p['nome'] = 'Obra · ' + ', '.join(selected)
                    commit()
                    st.success(f'{len(rows)} trechos e {len(reels)} bobinas importados.')
                    st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if p.get('avisos'):
            with st.expander(f"Observações da importação ({len(p['avisos'])})",expanded=True):
                for warning in p['avisos'][:80]:
                    st.write('• ' + warning)
    with tabs[1]:
        st.caption('O CSV permite cadastrar outros parques. Use os cabeçalhos do modelo; folga 0,05 corresponde a 5%.')
        demo = projects.demo()
        a,b = st.columns(2)
        for col,kind in [(a,'trechos'),(b,'bobinas')]:
            with col:
                st.download_button(f'Baixar modelo de {kind}',pd.DataFrame(demo[kind]).to_csv(index=False,sep=';').encode('utf-8-sig'),f'modelo_{kind}.csv', 'text/csv')
                f = st.file_uploader(f'CSV de {kind}',type='csv',key=f'csv_{kind}')
                if f and st.button(f'Substituir {kind}'):
                    try:
                        p[kind] = importer.import_csv(f.getvalue(),kind)
                        if kind == 'trechos':
                            p.update(subparques=sorted({r['parque'] for r in p['trechos']}),
                                     referencias_subparques={},arquivos_referencia={})
                        p['criterios_confirmados'] = False
                        commit()
                        st.success('Dados importados. Confira as telas de cadastro.')
                    except Exception as exc:
                        st.error(str(exc))
    with tabs[2]:
        saved = projects.saved_projects()
        if saved:
            choice = st.selectbox('Obras neste servidor',saved,format_func=lambda x:f'{x[1]} · {x[0][:8]}')
            if st.button('Abrir obra salva'):
                switch_project(projects.load(choice[0]))
        backup = st.file_uploader('Restaurar backup JSON',type='json')
        if backup and st.button('Restaurar como nova obra'):
            try:
                switch_project(projects.restore(backup.getvalue()))
            except Exception as exc:
                st.error(str(exc))
        a,b,c = st.columns(3)
        if a.button('Nova obra vazia'):
            switch_project(projects.new_project())
        if b.button('Abrir demonstração'):
            switch_project(projects.demo())
        if c.button('Duplicar obra atual'):
            new = copy.deepcopy(p)
            new['id'] = str(uuid.uuid4())
            new['nome'] += ' · cópia'
            projects.save(new)
            switch_project(new)
        st.caption('Projetos são salvos em SQLite neste servidor. Em hospedagens com disco temporário, mantenha backups JSON ou configure um volume persistente. Esta versão foi preparada para uso individual.')

elif page == 'Subparques':
    render_subparks(p)

elif page == 'Condutores':
    render_conductors(p)

elif page == 'Traçado':
    st.caption('Cada linha representa um condutor entre duas estruturas. A ordem pertence à combinação parque, circuito, nível, fase e rota.')
    st.info('Distância linear em metros; folga em fração (0,05 = 5%). Reserva é o acréscimo fixo em metros. Cadastre cada reserva física uma única vez por condutor.')
    fields = ['id','parque','circuito','nivel','fase','condutor','tipo','rota','ordem','de','para','linear','folga','reserva','corte_fim','fixa','bobina_original','observacao']
    df = pd.DataFrame(p['trechos'],columns=fields)
    park = st.selectbox('Filtrar parque',['Todos']+sorted(df.parque.dropna().unique().tolist()))
    subset = df if park == 'Todos' else df[df.parque == park]
    edited = st.data_editor(subset, num_rows='dynamic',hide_index=True,width='stretch',height=510,
        key=f'trechos_{st.session_state.edit_version}_{park}',
        column_config={'corte_fim':st.column_config.SelectboxColumn('Corte no fim',options=['PERMITIDO','PROIBIDO','OBRIGATORIO'],required=True),
                       'fase':st.column_config.SelectboxColumn('Fase',options=['A','B','C'],required=True),
                       'tipo':st.column_config.SelectboxColumn('Tipo',options=['AÉREO','SUBTERRÂNEO'],required=True),
                       'linear':st.column_config.NumberColumn('Linear [m]',min_value=0.01),
                       'folga':st.column_config.NumberColumn('Folga (fração)',min_value=0,max_value=1),
                       'reserva':st.column_config.NumberColumn('Reserva [m]',min_value=0),
                       'fixa':st.column_config.TextColumn('Bobina fixada',help='ID de uma bobina para preservar esta escolha na otimização.')})
    if st.button('Salvar alterações do traçado',type='primary'):
        clean = edited.copy()
        for k,default in [('rota','Principal'),('fixa',''),('observacao',''),('bobina_original',''),('corte_fim','PERMITIDO'),('reserva',0),('folga',.05)]:
            clean[k] = clean[k].fillna(default)
        remainder = df[df.parque != park] if park != 'Todos' else pd.DataFrame(columns=fields)
        previous = {r['id']:r for r in p['trechos']}
        p['trechos'] = [{**previous.get(r.get('id'),{}), **r} for r in records(pd.concat([remainder,clean],ignore_index=True))]
        p['criterios_confirmados'] = False
        commit()
        st.success('Traçado salvo. Revise novamente os critérios de corte.')
    if st.button('Conferir dados do projeto'):
        show_issues(engine.input_errors(p))

elif page == 'Resumo de bobinas':
    st.caption('Distribuição das bobinas entre os parques do controle importado e do projeto aberto. Todas as metragens estão em metros.')
    summary, parks, current = summarize(p)
    if not current:
        unassigned = sum(not r.get('bobina_original') for r in p['trechos'])
        if unassigned:
            st.warning(f'{unassigned} registro(s) de fase sem bobina. Os totais incluem somente os lançamentos com bobina atribuída.')
        known = {r['id'] for r in p['bobinas']}
        missing = sorted({r.get('bobina_original') for r in p['trechos'] if r.get('bobina_original') and r['bobina_original'] not in known})
        if missing:
            st.warning('Bobinas não cadastradas, fora dos totais: ' + ', '.join(missing))
    if not summary:
        st.info('Importe um controle Excel em Projeto e importação ou cadastre bobinas para visualizar o resumo.')
    else:
        if current:
            st.info('Visão atual: consumo dos outros parques + lançamentos do plano válido. Nos parques replanejados, o plano substitui os valores importados.')
        elif any('consumo_importado_parques' in r for r in p['bobinas']):
            st.info('Os subparques cadastrados alimentam este resumo pelos lançamentos e bobinas salvos. Os demais parques mantêm o histórico importado. Um plano válido passa a fornecer as alocações calculadas.')
        else:
            st.info('O resumo soma o consumo anterior aos lançamentos salvos em Subparques. As bobinas atribuídas a cada fase alimentam as colunas de cada parque.')
        if any('consumo_importado_parques' not in r for r in p['bobinas']):
            st.caption('Cadastros antigos ou manuais podem não ter histórico por parque. Esse consumo aparece em “Ajuste / sem parque”; reimporte o controle para obter a distribuição original.')
        df_summary = pd.DataFrame(summary)
        c1,c2,c3 = st.columns([2,2,1])
        query = c1.text_input('Buscar bobina ou condutor')
        conductor = c2.selectbox('Condutor',['Todos']+sorted(df_summary['Condutor'].unique().tolist()))
        exceeded = c3.checkbox('Somente excedidas')
        view = df_summary.copy()
        if query:
            view = view[view['Bobina'].str.contains(query,case=False,regex=False,na=False)|view['Condutor'].str.contains(query,case=False,regex=False,na=False)]
        if conductor != 'Todos':
            view = view[view['Condutor']==conductor]
        if exceeded:
            view = view[view['Saldo disponível [m]']<0]
        a,b,c,d = st.columns(4)
        a.metric('Bobinas na seleção',len(view))
        b.metric('Total utilizado',fmt(view['Total utilizado [m]'].sum())+' m')
        c.metric('Saldo líquido',fmt(view['Saldo disponível [m]'].sum())+' m')
        d.metric('Bobinas excedidas',int((view['Saldo disponível [m]']<0).sum()))
        if view['Situação'].str.contains('pendentes|duplicado',case=False,regex=True).any():
            st.warning('Há dados pendentes ou IDs duplicados. Valores desconhecidos não entram nos totais; registros duplicados permanecem visíveis para conferência.')
        numeric = parks+['Ajuste / sem parque [m]','Total utilizado [m]','Saldo disponível [m]','Base da bobina [m]','Nominal [m]','Real confirmada [m]']
        st.dataframe(view.style.apply(row_style,axis=1).format({k:'{:,.2f}' for k in numeric},na_rep='—',decimal=',',thousands='.'),
                     hide_index=True,width='stretch',height=500)
        st.caption('Vermelho: total utilizado maior que a base da bobina (saldo negativo). Base = metragem real, quando informada; caso contrário, nominal × 0,97. “Total” representa comprimento, não preço.')
        st.subheader('Resumo por condutor')
        grouped = view.groupby(['Condutor','Tipo'],dropna=False)[['Base da bobina [m]','Total utilizado [m]','Saldo disponível [m]']].sum(min_count=1).reset_index()
        st.dataframe(grouped.style.format({k:'{:,.2f}' for k in ['Base da bobina [m]','Total utilizado [m]','Saldo disponível [m]']},na_rep='—',decimal=',',thousands='.'),hide_index=True,width='stretch')
        st.caption('Edite o comprimento nominal, a metragem real e o consumo anterior na página Bobinas. O resumo acompanha as alterações salvas.')

elif page == 'Bobinas':
    registration=p.get('cadastros_aplicados',{}).get(MIGRATION)
    if registration:
        st.info(f"Estoque da referência cadastrado nesta obra: {registration['adicionadas']} bobinas adicionadas; {registration['existentes']} IDs existentes preservados. Origem: {registration['arquivo']}.")
    st.caption('Metragem real preenchida substitui a redução contratual de 3%. Deixe o campo vazio quando a metragem ainda não estiver confirmada.')
    fields = ['romaneio','id','condutor','tipo','nominal','real','utilizado']
    df = pd.DataFrame(p['bobinas'],columns=fields)
    df['_registro'] = list(range(len(df)))
    edited = st.data_editor(df, num_rows='dynamic',hide_index=True,width='stretch',height=450,
                           key=f'bobinas_{st.session_state.edit_version}',disabled=['_registro'],column_config={
                               '_registro':None,
                               'id':st.column_config.TextColumn('Bobina',required=True),
                               'nominal':st.column_config.NumberColumn('Nominal [m]',min_value=0),
                               'real':st.column_config.NumberColumn('Real confirmada [m]',min_value=0),
                               'utilizado':st.column_config.NumberColumn('Consumo anterior [m]',min_value=0),
                               'tipo':st.column_config.SelectboxColumn('Tipo',options=['AÉREO','SUBTERRÂNEO'])})
    if st.button('Salvar estoque e recalcular saldos',type='primary'):
        updated = []
        for record in records(edited):
            index = record.pop('_registro',None)
            previous = p['bobinas'][int(index)] if index is not None and 0 <= int(index) < len(p['bobinas']) else {}
            updated.append({**previous, **record})
        p['bobinas'] = updated
        old = p.get('plano')
        errors = engine.validate(p,old['cortes']) if old else engine.input_errors(p)
        if old and not errors:
            old['fingerprint'] = engine.fingerprint(p)
            old['status'] = 'Plano revalidado após alteração do estoque; otimização não refeita'
            commit(False)
            st.success('Estoque atualizado. O plano continua válido.')
        else:
            commit()
            if errors:
                show_issues(errors)
            else:
                st.success('Estoque atualizado.')
    st.subheader('Saldos calculados')
    try:
        st.dataframe(pd.DataFrame(engine.stock(p,(p.get('plano') or {}).get('cortes',[]))),hide_index=True,width='stretch')
    except Exception:
        st.warning('Preencha as metragens do cadastro para calcular os saldos.')

elif page == 'Critérios de corte':
    st.caption('As restrições se aplicam ao lançamento físico. Uma travessia contínua impede cortes em suas estruturas intermediárias.')
    a,b = st.columns([1,1.4])
    with a:
        st.subheader('Aproveitamento e prioridades')
        with st.form('criteria'):
            threshold = st.number_input('Sobra mínima reutilizável [m]',min_value=0,value=int(p['criterios']['sobra_minima']))
            wc = st.number_input('Peso por corte',min_value=1,value=int(p['criterios']['peso_cortes']))
            wb = st.number_input('Peso por bobina utilizada',min_value=0,value=int(p['criterios']['peso_bobinas']))
            wl = st.number_input('Peso por metro de sobra abaixo do limite',min_value=0,value=int(p['criterios']['peso_perda']))
            if st.form_submit_button('Salvar critérios'):
                p['criterios'].update(sobra_minima=threshold,peso_cortes=wc,peso_bobinas=wb,peso_perda=wl)
                commit()
                st.success('Critérios salvos.')
        st.caption('Os pesos definem a prioridade da otimização. Uma sobra pequena é sinalizada, mas não é descartada automaticamente do estoque.')
    with b:
        st.subheader('Aplicar restrição a uma travessia')
        if p['trechos']:
            park = st.selectbox('Parque',sorted({r['parque'] for r in p['trechos']}))
            circuits = sorted({r['circuito'] for r in p['trechos'] if r['parque'] == park})
            circuit = st.selectbox('Circuito',circuits)
            scope = [r for r in p['trechos'] if r['parque']==park and r['circuito']==circuit]
            structures = sorted({r['de'] for r in scope}|{r['para'] for r in scope})
            x,y = st.columns(2)
            start = x.selectbox('Início da região sem cortes',structures)
            end = y.selectbox('Fim da região sem cortes',structures,index=min(1,len(structures)-1))
            if st.button('Proibir cortes intermediários'):
                changes,conflicts = [],[]
                for chain in engine.segments(scope):
                    begins = [i for i,r in enumerate(chain) if r['de']==start]
                    ends = [i for i,r in enumerate(chain) if r['para']==end]
                    if len(begins)==1 and len(ends)==1 and begins[0]<=ends[0]:
                        block = chain[begins[0]:ends[0]+1]
                        changes.extend(block[:-1])
                        conflicts.extend(r['id'] for r in block[:-1] if r['corte_fim']=='OBRIGATORIO')
                if conflicts:
                    st.error('Há cortes obrigatórios dentro da região: '+', '.join(conflicts))
                elif changes:
                    for r in changes:
                        r['corte_fim']='PROIBIDO'
                    p['criterios_confirmados']=False
                    commit()
                    st.success(f'{len(changes)} restrições aplicadas. As extremidades foram preservadas.')
                else:
                    st.warning('Nenhum ponto intermediário encontrado nesta orientação. Confira de/para e a rota.')
        with st.expander('Aplicar folga percentual por tipo'):
            typ = st.selectbox('Tipo de instalação',['AÉREO','SUBTERRÂNEO'])
            percent = st.number_input('Folga [%]',min_value=0.0,max_value=100.0,value=5.0)
            if st.button('Aplicar a todos os trechos deste tipo'):
                for r in p['trechos']:
                    if r['tipo']==typ:
                        r['folga']=percent/100
                p['criterios_confirmados']=False
                commit()
                st.success('Folga atualizada. Reservas fixas preservadas.')
    st.divider()
    st.write('Para cortes obrigatórios ou restrições pontuais, edite “Corte no fim” na tela Traçado. Para preservar uma bobina, preencha “Bobina fixada”.')
    reviewed = st.checkbox('Conferi os pontos de amarração/corte, as travessias, as folgas e as reservas deste projeto.',value=p.get('criterios_confirmados',False),key=f'review_{st.session_state.edit_version}')
    if reviewed != p.get('criterios_confirmados',False):
        p['criterios_confirmados']=reviewed
        commit(False)

elif page == 'Plano e entregáveis':
    a,b,c = st.columns([1.3,1,1])
    mode = a.selectbox('Modo de cálculo',['Otimização global','Primeira solução viável'])
    seconds = b.number_input('Limite do solucionador [s]',min_value=5,max_value=300,value=30,step=5)
    c.write('')
    c.write('')
    if c.button('Validar entradas',width='stretch'):
        show_issues(engine.input_errors(p))
    if not p.get('criterios_confirmados'):
        st.warning('Revise e confirme os critérios de corte antes de gerar o plano.')
    x,y = st.columns(2)
    run = x.button('Gerar plano de corte',type='primary',disabled=not p.get('criterios_confirmados'),width='stretch')
    original = y.button('Consolidar bobinas da planilha importada',disabled=not p.get('criterios_confirmados'),width='stretch')
    if run or original:
        try:
            with st.spinner('Calculando lançamentos e validando o balanço de material…'):
                p['plano'] = engine.optimize(p,int(seconds),'global' if mode=='Otimização global' else 'rapido') if run else engine.consolidate_existing(p)
                commit(False)
            st.success(p['plano']['status'])
        except Exception as exc:
            p['plano']=None
            st.error(str(exc))
    plan = p.get('plano')
    if plan and plan['fingerprint'] != engine.fingerprint(p):
        st.warning('O plano está desatualizado. Calcule novamente.')
        plan = None
    if plan:
        cuts = plan['cortes']
        inventory = engine.stock(p,cuts)
        a,b,c,d = st.columns(4)
        a.metric('Lançamentos',len(cuts))
        b.metric('Bobinas utilizadas',len({r['bobina'] for r in cuts}))
        c.metric('Consumo de projeto',fmt(sum(r['projeto'] for r in cuts))+' m')
        d.metric('Cálculo',str(plan.get('segundos',0))+' s')
        st.caption(plan['status'])
        tabs = st.tabs(['Lançamentos contínuos','Resumo de bobinas','Ajuste manual','Exportação'])
        with tabs[0]:
            st.dataframe(pd.DataFrame(cuts).drop(columns='trechos'),hide_index=True,width='stretch')
            selected = st.selectbox('Rastrear os trechos de um lançamento',cuts,format_func=lambda c:f"{c['id']} · {c['fase']} · {c['de']} → {c['para']} · {c['bobina']}")
            st.dataframe(pd.DataFrame([r for r in p['trechos'] if r['id'] in selected['trechos']]),hide_index=True,width='stretch')
        with tabs[1]:
            st.dataframe(pd.DataFrame([r for r in inventory if r['reservado']]),hide_index=True,width='stretch')
        with tabs[2]:
            selected_cut = st.selectbox('Lançamento para trocar a bobina',cuts,format_func=lambda c:f"{c['id']} · {c['bobina']}",key='manual_cut')
            compatible = [r['id'] for r in p['bobinas'] if r['condutor']==selected_cut['condutor'] and r['tipo']==selected_cut['tipo']]
            target = st.selectbox('Nova bobina',compatible)
            fix = st.checkbox('Fixar esta bobina nas próximas otimizações',value=True)
            if st.button('Aplicar troca e validar'):
                candidate = copy.deepcopy(p)
                for r in candidate['trechos']:
                    if r['id'] in selected_cut['trechos']:
                        r['fixa']=target if fix else ''
                for cut in candidate['plano']['cortes']:
                    if cut['id']==selected_cut['id']:
                        cut['bobina']=target
                problems = engine.validate(candidate,candidate['plano']['cortes'])
                if problems:
                    show_issues(problems)
                else:
                    candidate['plano']['fingerprint']=engine.fingerprint(candidate)
                    candidate['plano']['status']='Plano ajustado manualmente e validado'
                    projects.save(candidate)
                    switch_project(candidate)
        with tabs[3]:
            st.write('Os arquivos usam o mesmo plano validado. O entregável contém lançamentos consolidados e resumo; o controle inclui os trechos e todo o estoque.')
            st.caption('Layout tabular próprio, com os campos do modelo enviado. Não copia assinaturas, logotipos ou status “liberado para execução” do documento de referência.')
            try:
                a,b = st.columns(2)
                a.download_button('Baixar controle Excel',export(p,'controle'),'Controle_RMT.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',width='stretch')
                b.download_button('Baixar entregável Excel',export(p,'entregavel'),'Plano_de_Corte_RMT.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',width='stretch')
            except Exception as exc:
                st.error(str(exc))
    elif not (run or original):
        st.info('Gere uma nova alocação ou consolide as bobinas já atribuídas no controle importado.')
